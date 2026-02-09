#!/bin/bash
set -ex

runserver_dev() {
    # Dev Server Config
    uvicorn src.main:app \
        --host 0.0.0.0 \
        --port 9000 \
        --workers 3 \
        --reload
}

case $1 in
    dev_server)
        chmod +x /app/docker/wait
        sh -c "/app/docker/wait"
        runserver_dev
        ;;

    *)
        eval "$@"
        ;;
esac
