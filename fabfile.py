from fabric.api import *

env.hosts = ['base102.net']


def push_local():
    local('git push origin master')  # runs the command on the local environment


def pull_remote():
    with cd('/opt/www/bitpay-shopify'):
        run('git pull')  # runs the command on the remote environment


def supervisor_cmd(cmd):
    sudo('supervisorctl %s' % cmd)


def supervisor_restart():
    supervisor_cmd('restart')


def supervisor_start():
    supervisor_cmd('start')


def supervisor_stop():
    supervisor_cmd('stop')


def nginx_cmd(cmd):
    sudo('/etc/init.d/nginx %s' % cmd)


def nginx_restart():
    nginx_cmd('restart')


def nginx_stop():
    nginx_cmd('stop')


def nginx_start():
    nginx_cmd('start')


def deploy():
    push_local()
    pull_remote()
    supervisor_restart()
    nginx_restart()
