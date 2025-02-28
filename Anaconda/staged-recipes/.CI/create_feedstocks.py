#!/usr/bin/env python
"""
Convert all recipes into feedstocks.

This script is to be run in a TravisCI context, with all secret environment variables defined (BINSTAR_TOKEN, GH_TOKEN)
Such as:

    export GH_TOKEN=$(cat ~/.conda-smithy/github.token)

"""
from __future__ import print_function

from conda_build.metadata import MetaData
from conda_smithy.github import gh_token
from contextlib import contextmanager
from datetime import datetime
from github import Github, GithubException, Team
import os.path
from random import choice
import shutil
import subprocess
import sys
import tempfile
import traceback


# Enable DEBUG to run the diagnostics, without actually creating new feedstocks.
DEBUG = False


superlative = ['awesome', 'slick', 'formidable', 'awe-inspiring', 'breathtaking',
               'magnificent', 'wonderous', 'stunning', 'astonishing', 'superb',
               'splendid', 'impressive', 'unbeatable', 'excellent', 'top', 'outstanding',
               'exalted', 'standout', 'smashing']


recipe_directory_name = 'recipes'
def list_recipes():
    if os.path.isdir(recipe_directory_name):
        recipes = os.listdir(recipe_directory_name)
    else:
        recipes = []

    for recipe_dir in recipes:
        # We don't list the "example" feedstock. It is an example, and is there
        # to be helpful.
        if recipe_dir.startswith('example'):
            continue
        path = os.path.abspath(os.path.join(recipe_directory_name, recipe_dir))
        yield path, MetaData(path).name()


@contextmanager
def tmp_dir(*args, **kwargs):
    temp_dir = tempfile.mkdtemp(*args, **kwargs)
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir)


def repo_exists(organization, name):
    token = gh_token()
    gh = Github(token)
    # Use the organization provided.
    org = gh.get_organization(organization)
    try:
        org.get_repo(name)
        return True
    except GithubException as e:
        if e.status == 404:
            return False
        raise


def create_team(org, name, description, repo_names):
    # PyGithub creates secret teams, and has no way of turning that off! :(
    post_parameters = {
        "name": name,
        "description": description,
        "privacy": "closed",
        "permission": "push",
        "repo_names": repo_names
    }
    headers, data = org._requester.requestJsonAndCheck(
        "POST",
        org.url + "/teams",
        input=post_parameters
    )
    return Team.Team(org._requester, headers, data, completed=True)

def print_rate_limiting_info(gh):
    # Compute some info about our GitHub API Rate Limit.
    # Note that it doesn't count against our limit to
    # get this info. So, we should be doing this regularly
    # to better know when it is going to run out. Also,
    # this will help us better understand where we are
    # spending it and how to better optimize it.

    # Get GitHub API Rate Limit usage and total
    gh_api_remaining, gh_api_total = gh.rate_limiting

    # Compute time until GitHub API Rate Limit reset
    gh_api_reset_time = gh.rate_limiting_resettime
    gh_api_reset_time = datetime.utcfromtimestamp(gh_api_reset_time)
    gh_api_reset_time -= datetime.utcnow()

    print("")
    print("GitHub API Rate Limit Info:")
    print("---------------------------")
    print("Currently remaining {remaining} out of {total}.".format(remaining=gh_api_remaining, total=gh_api_total))
    print("Will reset in {time}.".format(time=gh_api_reset_time))
    print("")



if __name__ == '__main__':
    exit_code = 0

    is_merged_pr = (os.environ.get('TRAVIS_BRANCH') == 'master' and os.environ.get('TRAVIS_PULL_REQUEST') == 'false')

    smithy_conf = os.path.expanduser('~/.conda-smithy')
    if not os.path.exists(smithy_conf):
        os.mkdir(smithy_conf)

    def write_token(name, token):
        with open(os.path.join(smithy_conf, name + '.token'), 'w') as fh:
            fh.write(token)
    if 'APPVEYOR_TOKEN' in os.environ:
        write_token('appveyor', os.environ['APPVEYOR_TOKEN'])
    if 'CIRCLE_TOKEN' in os.environ:
        write_token('circle', os.environ['CIRCLE_TOKEN'])
    gh = None
    if 'GH_TOKEN' in os.environ:
        write_token('github', os.environ['GH_TOKEN'])
        gh = Github(os.environ['GH_TOKEN'])

        # Get our initial rate limit info.
        print_rate_limiting_info(gh)


    owner_info = ['--organization', 'conda-forge']

    print('Calculating the recipes which need to be turned into feedstocks.')
    with tmp_dir('__feedstocks') as feedstocks_dir:
        feedstock_dirs = []
        for recipe_dir, name in list_recipes():
            feedstock_dir = os.path.join(feedstocks_dir, name + '-feedstock')
            print('Making feedstock for {}'.format(name))

            subprocess.check_call(['conda', 'smithy', 'init', recipe_dir,
                                   '--feedstock-directory', feedstock_dir])
            if not is_merged_pr:
                # We just want to check that conda-smithy is doing its thing without having any metadata issues.
                continue

            feedstock_dirs.append([feedstock_dir, name, recipe_dir])

            subprocess.check_call(['git', 'remote', 'add', 'upstream_with_token',
                                   'https://conda-forge-manager:{}@github.com/conda-forge/{}-feedstock'.format(os.environ['GH_TOKEN'],
                                                                                                               name)],
                                  cwd=feedstock_dir)

            # Sometimes we already have the feedstock created. We need to deal with that case.
            if repo_exists('conda-forge', name + '-feedstock'):
                subprocess.check_call(['git', 'fetch', 'upstream_with_token'], cwd=feedstock_dir)
                subprocess.check_call(['git', 'branch', '-m', 'master', 'old'], cwd=feedstock_dir)
                try:
                    subprocess.check_call(['git', 'checkout', '-b', 'master', 'upstream_with_token/master'], cwd=feedstock_dir)
                except subprocess.CalledProcessError:
                    # Sometimes, we have a repo, but there are no commits on it! Just catch that case.
                    subprocess.check_call(['git', 'checkout', '-b' 'master'], cwd=feedstock_dir)
            else:
                subprocess.check_call(['conda', 'smithy', 'register-github', feedstock_dir] + owner_info)

        conda_forge = None
        teams = None
        if gh:
            # Only get the org and teams if there is stuff to add.
            if feedstock_dirs:
                conda_forge = gh.get_organization('conda-forge')
                teams = {team.name: team for team in conda_forge.get_teams()}

        # Break the previous loop to allow the TravisCI registering to take place only once per function call.
        # Without this, intermittent failures to synch the TravisCI repos ensue.
        all_maintainers = set()
        # Hang on to any CI registration errors that occur and raise them at the end.
        for feedstock_dir, name, recipe_dir in feedstock_dirs:
            # Try to register each feedstock with CI.
            # However sometimes their APIs have issues for whatever reason.
            # In order to bank our progress, we note the error and handle it.
            # After going through all the recipes and removing the converted ones,
            # we fail the build so that people are aware that things did not clear.
            try:
                subprocess.check_call(['conda', 'smithy', 'register-ci', '--feedstock_directory', feedstock_dir] + owner_info)
            except subprocess.CalledProcessError:
                exit_code = 1
                traceback.print_exception(*sys.exc_info())
                continue

            subprocess.check_call(['conda', 'smithy', 'rerender'], cwd=feedstock_dir)
            subprocess.check_call(['git', 'commit', '-am', "Re-render the feedstock after CI registration."], cwd=feedstock_dir)
            for i in range(5):
                try:
                    # Capture the output, as it may contain the GH_TOKEN.
                    out = subprocess.check_output(['git', 'push', 'upstream_with_token', 'HEAD:master'], cwd=feedstock_dir,
                                                  stderr=subprocess.STDOUT)
                    break
                except subprocess.CalledProcessError:
                    pass

                # Likely another job has already pushed to this repo.
                # Place our changes on top of theirs and try again.
                out = subprocess.check_output(['git', 'fetch', 'upstream_with_token', 'master'], cwd=feedstock_dir,
                                              stderr=subprocess.STDOUT)
                try:
                    subprocess.check_call(['git', 'rebase', 'upstream_with_token/master', 'master'], cwd=feedstock_dir)
                except subprocess.CalledProcessError:
                    # Handle rebase failure by choosing the changes in `master`.
                    subprocess.check_call(['git', 'checkout', 'master', '--', '.'], cwd=feedstock_dir)
                    subprocess.check_call(['git', 'rebase', '--continue'], cwd=feedstock_dir)

            # Add team members as maintainers.
            if conda_forge:
                meta = MetaData(recipe_dir)
                maintainers = set(meta.meta.get('extra', {}).get('recipe-maintainers', []))
                all_maintainers.update(maintainers)
                team_name = name.lower()
                repo_name = 'conda-forge/{}-feedstock'.format(name)

                # Try to get team or create it if it doesn't exist.
                team = teams.get(team_name)
                if not team:
                    team = create_team(
                        conda_forge,
                        team_name,
                        'The {} {} contributors!'.format(choice(superlative), team_name),
                        repo_names=[repo_name]
                    )
                    teams[team_name] = team
                    current_maintainers = []
                else:
                    current_maintainers = team.get_members()

                # Add only the new maintainers to the team.
                current_maintainers_handles = set([each_maintainers.login.lower() for each_maintainers in current_maintainers])
                for new_maintainer in maintainers - current_maintainers_handles:
                    headers, data = team._requester.requestJsonAndCheck(
                        "PUT",
                        team.url + "/memberships/" + new_maintainer
                    )
                # Mention any maintainers that need to be removed (unlikely here).
                for old_maintainer in current_maintainers_handles - maintainers:
                    print("AN OLD MEMBER ({}) NEEDS TO BE REMOVED FROM {}".format(old_maintainer, repo_name))

            # Remove this recipe from the repo.
            if is_merged_pr:
                subprocess.check_call(['git', 'rm', '-r', recipe_dir])

    # Add new conda-forge members to all-members team. Welcome! :)
    if conda_forge:
        team_name = 'all-members'
        team = teams.get(team_name)
        if not team:
            team = create_team(
                conda_forge,
                team_name,
                'All of the awesome conda-forge contributors!',
                []
            )
            teams[team_name] = team
            current_members = []
        else:
            current_members = team.get_members()

        # Add only the new members to the team.
        current_members_handles = set([each_member.login.lower() for each_member in current_members])
        for new_member in all_maintainers - current_members_handles:
            print("Adding a new member ({}) to conda-forge. Welcome! :)".format(new_member))
            headers, data = team._requester.requestJsonAndCheck(
                "PUT",
                team.url + "/memberships/" + new_member
            )

    # Update status based on the remote.
    subprocess.check_call(['git', 'stash', '--keep-index', '--include-untracked'])
    subprocess.check_call(['git', 'fetch'])
    subprocess.check_call(['git', 'rebase', '--autostash'])
    subprocess.check_call(['git', 'add', '.'])
    try:
        subprocess.check_call(['git', 'stash', 'pop'])
    except subprocess.CalledProcessError:
        # In case there was nothing to stash.
        # Finish quietly.
        pass

    # Parse `git status --porcelain` to handle some merge conflicts and generate the removed recipe list.
    changed_files = subprocess.check_output(['git', 'status', '--porcelain', recipe_directory_name],
                                            universal_newlines=True)
    changed_files = changed_files.splitlines()

    # Add all files from AU conflicts. They are new files that we weren't tracking previously.
    # Adding them resolves the conflict and doesn't actually add anything to the index.
    new_file_conflicts = filter(lambda _: _.startswith("AU "), changed_files)
    new_file_conflicts = map(lambda _ : _.replace("AU", "", 1).lstrip(), new_file_conflicts)
    for each_new_file in new_file_conflicts:
        subprocess.check_call(['git', 'add', each_new_file])

    # Generate a fresh listing of recipes removed.
    #
    # * Each line we get back is a change to a file in the recipe directory.
    # * We narrow the list down to recipes that are staged for deletion (ignores examples).
    # * Then we clean up the list so that it only has the recipe names.
    removed_recipes = filter(lambda _: _.startswith("D "), changed_files)
    removed_recipes = map(lambda _ : _.replace("D", "", 1).lstrip(), removed_recipes)
    removed_recipes = map(lambda _ : os.path.relpath(_, recipe_directory_name), removed_recipes)
    removed_recipes = map(lambda _ : _.split(os.path.sep)[0], removed_recipes)
    removed_recipes = sorted(set(removed_recipes))

    # Commit any removed packages.
    subprocess.check_call(['git', 'status'])
    if removed_recipes:
        msg = ('Removed recipe{s} ({}) after converting into feedstock{s}.'
               ''.format(', '.join(removed_recipes),
                         s=('s' if len(removed_recipes) > 1 else '')))
        msg += ' [ci skip]' if exit_code == 0 else ' [skip appveyor]'
        if is_merged_pr:
            # Capture the output, as it may contain the GH_TOKEN.
            out = subprocess.check_output(['git', 'remote', 'add', 'upstream_with_token',
                                           'https://conda-forge-manager:{}@github.com/conda-forge/staged-recipes'.format(os.environ['GH_TOKEN'])],
                                          stderr=subprocess.STDOUT)
            subprocess.check_call(['git', 'commit', '-m', msg])
            # Capture the output, as it may contain the GH_TOKEN.
            branch = os.environ.get('TRAVIS_BRANCH')
            out = subprocess.check_output(['git', 'push', 'upstream_with_token', 'HEAD:%s' % branch],
                                          stderr=subprocess.STDOUT)
        else:
            print('Would git commit, with the following message: \n   {}'.format(msg))

    if gh:
        # Get our final rate limit info.
        print_rate_limiting_info(gh)

    sys.exit(exit_code)
