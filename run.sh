#!/bin/bash
# This script is run automatically when the pi runs, directly from /etc/xdg/autostart/koa-bot.desktop
# You can define the environmental variables either in ./.env or at ~/.profile

MIN_PYTHON_VERSION="3.7.3"

# Checking XDG variables
# https://stackoverflow.com/questions/40223060/home-vs-for-use-in-bash-scripts
XDG_CONFIG_HOME=${XDG_CONFIG_HOME:-"$HOME/.config"}
XDG_CACHE_HOME=${XDG_CACHE_HOME:-"$HOME/.cache"}
XDG_DATA_HOME=${XDG_DATA_HOME:-"$HOME/.local/share"}

# Loading .env file
if [ -f .env ]; then
    export $(echo $(cat .env | sed 's/#.*//g'| xargs) | envsubst)
fi

function show_help() {
    cat << EOF
Usage: ${0##*/} [OPTION...]
  -h, --help
  -i, --install
  -u, --update
  -U, --update-dependencies
  -r, --restart
EOF
}

function var_is_defined() {
    [ -v $1 ]
}

function var_is_empty() {
    [ -z "${1}" ]
}

function path_is_valid() {
    [ -d "${1}" ]
}

function command_exists() {
    command -v $1 1> /dev/null 2>&1;
}

function check_env_vars() {
    if ! var_is_defined KOAKUMA_HOME; then
        echo "\$KOAKUMA_HOME is not defined. It needs to point to the bot's directory."
        exit 1
    fi

    if ! path_is_valid "${KOAKUMA_HOME}"; then
        echo "Missing bot directory or env var set incorrectly, it points to ${KOAKUMA_HOME}"
        exit 1
    fi

    if ! var_is_defined KOAKUMA_CONNSTR; then
        echo "\$KOAKUMA_CONNSTR is not defined. It needs to point to the bot's hosting machine."
        exit 1
    fi
}

function test_conectivity() {
    check_env_vars

    # Redirects STDERR to /dev/null to hide ssh error messages
    REMOTE_HOME=$(ssh "${KOAKUMA_CONNSTR}" 'source ~/.profile; echo $KOAKUMA_HOME' 2> /dev/null)
    ssh_return_value=$?

    # Test if host is up
    if [ $ssh_return_value -ne 0 ]; then
        echo "Unable to connect to host ("${KOAKUMA_CONNSTR}") [Return value: $ssh_return_value]"
        exit 1
    fi

    if ! var_is_defined REMOTE_HOME; then
        echo "The remote \$KOAKUMA_HOME env var is empty or set incorrectly."
        exit 1
    fi
}

function update_dependencies() {
    echo "Updating bot dependencies..."

    if [ ! -n "$1" ]; then
        test_conectivity
    fi

    PIP_OUTPUT=$(ssh "${KOAKUMA_CONNSTR}" 'source ~/.profile; pip3 install -r $KOAKUMA_HOME/requirements.txt')
    echo $PIP_OUTPUT
}

function update() {
    # Automatically sends updates to the bot. In the future it should also restart the running instance.
    echo "Updating bot files..."

    if [ ! -n "$1" ]; then
        test_conectivity
    fi

    TARGET_KOAHOME="${KOAKUMA_CONNSTR}:${REMOTE_HOME}"
    TARGET_KOACONFIG="${KOAKUMA_CONNSTR}:~/.config/koa-bot"

    echo "Transferring source from ${KOAKUMA_HOME} to ${TARGET_KOAHOME}"
    rsync -aAXv --include=.python-version --exclude=.* --exclude=__pycache__ --exclude=venv --progress "${KOAKUMA_HOME}/" "${TARGET_KOAHOME}"
    echo
    echo "Transferring config files from ${XDG_CONFIG_HOME}/koa-bot/ to ${TARGET_KOACONFIG}"
    rsync -aAXv --progress "${XDG_CONFIG_HOME}/koa-bot/" "${TARGET_KOACONFIG}"
}

function restart() {
    echo "Not yet implemented!"
}

function run() {
    echo "Starting bot..."
    cd "${KOAKUMA_HOME}"

    # pyenv specific
    if ! command_exists pyenv; then
        export PYENV_ROOT=$HOME/.pyenv
        export PATH="$PYENV_ROOT/bin:$PATH"
    fi

    if command_exists pyenv; then
        export PYENV_VIRTUALENV_DISABLE_PROMPT=1
        eval "$(pyenv init -)"
        eval "$(pyenv virtualenv-init -)"
        pyenv activate koa-bot
    fi

    python3 -m koabot
}

function install() {
    # System dependencies
    # NOTE: ffmpeg is necessary to play music
    local package_deps=(ffmpeg)

    for pdep in ${package_deps[*]}; do
        if ! command_exists $pdep; then
            pckgs="${pckgs}${pdep} "
        fi
    done

    if ! var_is_empty $pckgs; then
        # TODO: check if user cancels or apt errors out
        sudo apt install ${pckgs} -y
    else
        echo "Required system dependencies met."
    fi

    # Python dependencies
    MIN_PYTHON_VERSION=($(echo "$MIN_PYTHON_VERSION" | grep -o -E '[0-9]+'))

    if [ ${#MIN_PYTHON_VERSION[@]} -gt 3 ]; then
        echo "Invalid minimum python version requirement. Exiting."
        exit 1
    fi

    for p in python python3; do
        if command_exists $p; then
            PYTHON_BIN=$p
            break
        fi
    done

    if ! var_is_defined PYTHON_BIN; then
        echo "Couldn't find 'python' in system."
        exit 1
    fi

    PYTHON_VERSION=($(echo $($PYTHON_BIN -c 'import platform; major, minor, patch = platform.python_version_tuple(); print(major); print(minor); print(patch);')))

    for (( i=0; i<${#MIN_PYTHON_VERSION[@]}; i++ )); do
        if [ ${PYTHON_VERSION[i]} -lt ${MIN_PYTHON_VERSION[i]} ]; then
            echo "Minimum python version requirement not met. Exiting."
            exit 1
        fi
    done

    echo "Installing python dependencies..."
    $PYTHON_BIN -m pip install -r requirements.txt
}

if [ -n "$1" ]; then
    # If there's options
    while [ -n "$1" ]; do
        case "$1" in
            -h|--help) show_help;;
            -i|--install) install;;
            -uU|-Uu)
                test_conectivity
                update "skip_conn_test"
                update_dependencies "skip_conn_test"
            ;;
            -u|--update) update;;
            -U|--update-dependencies) update_dependencies;;
            -r|--restart) restart;;
        esac

        shift
    done
else
    # No options: run the bot
    run

    # Prevent terminal from closing
    read -p "Bot terminated."
fi
