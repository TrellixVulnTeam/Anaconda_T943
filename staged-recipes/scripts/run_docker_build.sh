#!/usr/bin/env bash

# NOTE: This script has been adapted from content generated by github.com/conda-forge/conda-smithy

REPO_ROOT=$(cd "$(dirname "$0")/.."; pwd;)
IMAGE_NAME="condaforge/linux-anvil"

config=$(cat <<CONDARC

channels:
 - conda-forge
 - defaults

conda-build:
 root-dir: /staged-recipes/build_artefacts

always_yes: true
show_channel_urls: true

CONDARC
)

cat << EOF | docker run -i \
                        -v ${REPO_ROOT}:/staged-recipes \
                        -a stdin -a stdout -a stderr \
                        $IMAGE_NAME \
                        bash || exit $?

# Copy the host recipes folder so we don't ever muck with it
cp -r /staged-recipes/recipes /conda-recipes

# Find the recipes from master in this PR and remove them.
echo "Finding recipes merged in master and removing them from the build."
pushd /staged-recipes/recipes > /dev/null
git ls-tree --name-only master -- . | xargs -I {} sh -c "rm -rf /conda-recipes/{} && echo Removing recipe: {}"
popd > /dev/null

if [ "${BINSTAR_TOKEN}" ];then
    export BINSTAR_TOKEN=${BINSTAR_TOKEN}
fi

# Unused, but needed by conda-build currently... :(
export CONDA_NPY='19'

echo "$config" > ~/.condarc

# A lock sometimes occurs with incomplete builds. The lock file is stored in build_artefacts.
conda clean --lock

conda update conda conda-build
conda install conda-build-all
conda install conda-forge-build-setup
source run_conda_forge_build_setup

# yum installs anything from a "yum_requirements.txt" file that isn't a blank line or comment.
find conda-recipes -mindepth 2 -maxdepth 2 -type f -name "yum_requirements.txt" \
    | xargs -n1 cat | grep -v -e "^#" -e "^$" | \
    xargs -r yum install -y

conda-build-all /conda-recipes --matrix-conditions "numpy >=1.11" "python >=2.7,<3|>=3.5" "r-base >=3.3.2"
EOF
