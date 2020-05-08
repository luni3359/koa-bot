#!/bin/bash
# This script is run automatically when the pi runs, directly from /etc/xdg/autostart/koa-bot.desktop
# env var is defined at ~/.profile

function var_is_defined() {
    [[ -v $1 ]]
}

function path_is_valid() {
    if [ ! -d ${1} ]; then
        false
    fi
    true
}

function check_env_vars() {
    if ! var_is_defined "${KOAKUMA_HOME}"; then
        echo "\$KOAKUMA_HOME is not defined. It needs to point to the bot's directory."
        exit 1
    fi

    if ! path_is_valid "${KOAKUMA_HOME}"; then
        echo "Missing bot directory or env var set incorrectly, it points to ${KOAKUMA_HOME}"
        exit 1
    fi

    if ! var_is_defined "${KOAKUMA_CONNSTR}"; then
        echo "\$KOAKUMA_CONNSTR is not defined. It needs to point to the bot's hosting machine."
        exit 1
    fi
}

function test_conectivity() {
    check_env_vars

    # redirects STDERR to /dev/null to hide ssh error messages
    REMOTE_HOME=$(ssh "${KOAKUMA_CONNSTR}" 'source ~/.profile; echo $KOAKUMA_HOME' 2> /dev/null)
    ssh_return_value=$?

    # Test if host is up
    if [ $ssh_return_value -ne 0 ]; then
        echo "Unable to connect to host ("${KOAKUMA_CONNSTR}") [Return value: $ssh_return_value]"
        exit 1
    fi

    if ! var_is_defined "${REMOTE_HOME}"; then
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

function run() {
    echo "Starting bot..."
    cd "${KOAKUMA_HOME}"
    python3 -m koabot
}

function command_exists() {
    command -v $1 1> /dev/null 2>&1;
}

function install_package() {
    echo "Installing $1..."
    # sudo apt install $1
    echo "$1 has been installed."
}

function install() {
    package_deps=(ffmpeg mariadb-server)
    for pdep in ${package_deps[*]}; do
        if ! command_exists $pdep; then
            pckgs="${pckgs}${pdep} "
        fi
    done

    # dummy string
    echo "apt install ${pckgs} -y"

    # ffmpeg is necessary to play music
    if ! command_exists ffmpeg; then
        install_package ffmpeg
    fi

    if ! command_exists mariadb-server; then
        install_package mariadb-server
    fi

    if ! command_exists python3; then
        python3 -V
    else
        if ! command_exists python; then
            python -V
        fi
    fi

    pip install -r requirements.txt
}

# set XDG variables
# https://stackoverflow.com/questions/40223060/home-vs-for-use-in-bash-scripts
if ! var_is_defined "${XDG_CONFIG_HOME}"; then
    XDG_CONFIG_HOME=~/.config/
fi

if ! var_is_defined "${XDG_CACHE_HOME}"; then
    XDG_CACHE_HOME=~/.cache/
fi

if ! var_is_defined "${XDG_DATA_HOME}"; then
    XDG_DATA_HOME=~/.local/share
fi

# If there's options
if [ -n "$1" ]; then
    while [ -n "$1" ]; do
        case "$1" in
            -i|--install) install;;
            -uU|-Uu)
                test_conectivity
                update "skip_conn_test"
                update_dependencies "skip_conn_test"
            ;;
            -u|--update) update;;
            -U|--update-dependencies) update_dependencies;;
            -r|--restart) ;;
        esac

        shift
    done
else
    # No options: run the bot
    run
fi
