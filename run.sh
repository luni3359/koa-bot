#!/bin/bash
# This script is run automatically when the pi runs, directly from /etc/xdg/autostart/koa-bot.desktop
# env var is set at ~/.profile

function check_env_vars() {
    if [ -z ${KOAKUMA_HOME} ]; then
        echo "\$KOAKUMA_HOME is not defined. It needs to point to the bot's directory."
        exit 1
    fi

    if [ ! -d ${KOAKUMA_HOME} ]; then
        echo "Missing bot directory or env var set incorrectly, it points to ${KOAKUMA_HOME}"
        exit 1
    fi

    if [ -z ${KOAKUMA_CONNSTR} ]; then
        echo "\$KOAKUMA_CONNSTR is not defined. It needs to point to the bot's hosting machine."
        exit 1
    fi
}

function test_conectivity() {
    check_env_vars

    # redirects STDERR to /dev/null to hide ssh error messages
    REMOTE_HOME=$(ssh ${KOAKUMA_CONNSTR} 'source ~/.profile; echo $KOAKUMA_HOME' 2> /dev/null)
    ssh_return_value=$?

    # Test if host is up
    if [ $ssh_return_value -ne 0 ]; then
        echo "Unable to connect to host (${KOAKUMA_CONNSTR}) [Return value: $ssh_return_value]"
        exit 1
    fi

    if [ -z ${REMOTE_HOME} ]; then
        echo "The remote \$KOAKUMA_HOME env var is empty or set incorrectly."
        exit 1
    fi

    # Appending home of the remote koakuma
    TARGET=${KOAKUMA_CONNSTR}:${REMOTE_HOME}
}

function update_dependencies() {
    echo "Updating bot dependencies..."

    if [ ! -n "$1" ]; then
        test_conectivity
    fi

    PIP_OUTPUT=$(ssh ${KOAKUMA_CONNSTR} 'source ~/.profile; pip3 install -r $KOAKUMA_HOME/requirements.txt')
    echo $PIP_OUTPUT
}

function update() {
    # Automatically sends updates to the bot. In the future it should also restart the running instance.
    echo "Updating bot files..."

    if [ ! -n "$1" ]; then
        test_conectivity
    fi

    echo "Transferring from ${KOAKUMA_HOME} to ${TARGET}"

    rsync -aXv --include=.python-version --exclude=.* --exclude=__pycache__ --exclude=venv --progress ${KOAKUMA_HOME}/ ${TARGET}
    echo
}

function run() {
    echo "Starting bot..."
    cd ${KOAKUMA_HOME}
    python3 -m koabot
}

function package_is_not_installed() {
    if ! dpkg -l $1 >/dev/null 2>&1; then
        echo "$1 is not installed in the system."
        return 1
    else
        echo "$1 is already installed."
        return 0
    fi
}

function install_package() {
    echo "Installing $1..."
    # sudo apt install $1
    echo "$1 has been installed."
}

function install() {
    # Necessary package to play music
    package_is_not_installed ffmpeg
    if [ ! $? ]; then
        install_package ffmpeg
    fi

    package_is_not_installed mariadb-server
    if [ ! $? ]; then
        install_package mariadb-server
    fi

    package_is_not_installed python3
    if [ ! $? ]; then
        python3 -V
    else
        package_is_not_installed python
        if [ ! $? ]; then
            python -V
        fi
    fi

    pip install -r requirements.txt
}

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
