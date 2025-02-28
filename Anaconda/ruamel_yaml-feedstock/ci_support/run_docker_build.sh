#!/usr/bin/env bash

# PLEASE NOTE: This script has been automatically generated by conda-smithy. Any changes here
# will be lost next time ``conda smithy rerender`` is run. If you would like to make permanent
# changes to this script, consider a proposal to conda-smithy so that other feedstocks can also
# benefit from the improvement.

FEEDSTOCK_ROOT=$(cd "$(dirname "$0")/.."; pwd;)
RECIPE_ROOT=$FEEDSTOCK_ROOT/recipe

docker info

config=$(cat <<CONDARC

channels:
 - conda-forge
 - defaults

conda-build:
 root-dir: /feedstock_root/build_artefacts

show_channel_urls: true

CONDARC
)

rm -f "$FEEDSTOCK_ROOT/build_artefacts/conda-forge-build-done"

cat << EOF | docker run -i \
                        -v "${RECIPE_ROOT}":/recipe_root \
                        -v "${FEEDSTOCK_ROOT}":/feedstock_root \
                        -a stdin -a stdout -a stderr \
                        condaforge/linux-anvil \
                        bash || exit 1

export BINSTAR_TOKEN=${BINSTAR_TOKEN}
export PYTHONUNBUFFERED=1

echo "$config" > ~/.condarc
# A lock sometimes occurs with incomplete builds. The lock file is stored in build_artefacts.
conda clean --lock

conda install --yes --quiet conda-forge-build-setup
source run_conda_forge_build_setup

# Embarking on 3 case(s).
    set -x
    export CONDA_PY=27
    set +x
    conda build /recipe_root --quiet || exit 1
    upload_or_check_non_existence /recipe_root conda-forge --channel=main || exit 1

    set -x
    export CONDA_PY=35
    set +x
    conda build /recipe_root --quiet || exit 1
    upload_or_check_non_existence /recipe_root conda-forge --channel=main || exit 1

    set -x
    export CONDA_PY=36
    set +x
    conda build /recipe_root --quiet || exit 1
    upload_or_check_non_existence /recipe_root conda-forge --channel=main || exit 1
touch /feedstock_root/build_artefacts/conda-forge-build-done
EOF

# double-check that the build got to the end
# see https://github.com/conda-forge/conda-smithy/pull/337
# for a possible fix
set -x
test -f "$FEEDSTOCK_ROOT/build_artefacts/conda-forge-build-done" || exit 1
