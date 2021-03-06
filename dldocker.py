#!/usr/bin/env python3

import os
from os import path
from os.path import join
import re
import importlib
import argparse
import subprocess
from datetime import datetime
from functools import partial


run = partial(subprocess.run, shell=True, encoding='utf-8')


def log(msg, file=None, time_prefix=True):
    if msg:
        if time_prefix:
            msg = ('[%s]: ' % datetime.now()) + msg
        if file is not None:
            print(msg)
        print(msg, file=file)


def process_config(config, config_name):
    import configs.defaults as defaults

    # Filling defaults for missing keys.
    for k in dir(defaults):
        if not k.startswith('__') and not hasattr(config, k):
            setattr(config, k, getattr(defaults, k))

    whoami = run('whoami', stdout=subprocess.PIPE).stdout.strip() or ''

    image_prefix = config.IMAGE_PREFIX or whoami

    base_image_suffix = config.BASE_IMAGE_SUFFIX or ''

    config.BASE_IMAGE_NAME = config.BASE_IMAGE_NAME or \
        f'{image_prefix}/base{base_image_suffix}:gpu'

    config.LAB_CONTAINER_PREFIX = config.LAB_CONTAINER_PREFIX \
        if config.LAB_CONTAINER_PREFIX \
        else whoami + '-'

    lab_image_suffix = config.LAB_IMAGE_SUFFIX or ''

    if config.LAB_CONTAINER_SUFFIX:
        lab_container_suffix = config.LAB_CONTAINER_SUFFIX
    else:
        lab_container_suffix = f'-{config_name}'

    config.LAB_IMAGE_NAME = config.LAB_IMAGE_NAME or \
        f'{image_prefix}/lab{lab_image_suffix}:gpu'

    config.LAB_CONTAINER_NAME = config.LAB_CONTAINER_NAME or \
        f'{config.LAB_CONTAINER_PREFIX}lab{lab_container_suffix}'

    config.NOTEBOOK_DIR = config.NOTEBOOK_DIR or \
        '/workspace/projects'

    config.MOUNTPOINT = config.MOUNTPOINT or \
        '$HOME/projects:/workspace/projects'

    config.SSHD_PORT = config.SSHD_PORT or \
        '8890:22'

    config.JUPYTERLAB_PORT = config.JUPYTERLAB_PORT or \
        '8889:8888'

    config.TENSORBOARD_PORT = config.TENSORBOARD_PORT or \
        '8899:6006'

    config.HOSTNAME = config.HOSTNAME or \
        'dl-server'

    return config


def parse_args():
    configs = [x.replace('.py', '') for x in os.listdir(join('configs')) if x.endswith('.py') and x != 'defaults.py']

    parser = argparse.ArgumentParser(
        description='Main script for building and running deep learning images and containers.'
    )
    parser.add_argument(
        '-c',
        '--config',
        help='Configuration contaning image tag, container name and build configuration.',
        default='tf2',
        choices=configs
    )
    parser.add_argument(
        '-d',
        '--dry-run',
        help='Dry run.',
        action='store_true'
    )
    parser.add_argument(
        '-a',
        '--autoports',
        help='Select ports automatically.',
        action='store_true'
    )

    parser_cmd = parser.add_subparsers(dest='command', title='command')
    parser_cmd.required = True

    parser_update_path = parser_cmd.add_parser(
        'update-path',
        help='Add path to the directory containing this script to $PATH shell variable.'
    )

    parser_build = parser_cmd.add_parser(
        'build',
        help='Builds image.'
    )
    parser_build.add_argument(
        '-s',
        '--skip-base',
        help='Skips building of base image.',
        action='store_true'
    )
    parser_build.add_argument(
        '--use-cache',
        help='Use cache when building images.',
        action='store_true'
    )

    parser_run_jl = parser_cmd.add_parser(
        'run-jl',
        help='Runs a new container and starts jupyterlab with sshd.'
    )
    parser_run_jl.add_argument(
        '--mountpoint',
        help='Container mount point in format host_path:container_path.',
    )
    parser_run_jl.add_argument(
        '-v',
        '--mountpoints',
        help='Additional mount points in format host_path:container_path.',
        nargs='*'
    )
    parser_run_jl.add_argument(
        '--notebook-dir',
        help='Path to notebooks directory inside container.',
    )
    parser_run_jl.add_argument(
        '-m', '--memory',
        help='Memory limit.',
        default='32g'
    )
    parser_run_jl.add_argument(
        '-g', '--group',
        help='Run container with group id instead of $(id -g).',
    )
    parser_run_jl.add_argument(
        '--python_buffer',
        help='Run container with buffering python logs',
        type=int,
        default=1
    )

    parser_run_it = parser_cmd.add_parser(
        'run-it',
        help='Interactively runs specified command in a new container.'
    )
    parser_run_it.add_argument(
        '--mountpoint',
        help='Container mount point in format host_path:container_path.',
    )
    parser_run_it.add_argument(
        '-v',
        '--mountpoints',
        help='Additional mount points in format host_path:container_path.',
        nargs='*'
    )
    parser_run_it.add_argument(
        '-m', '--memory',
        help='Memory limit.',
        default='32g'
    )
    parser_run_it.add_argument(
        '-g', '--group',
        help='Run container with group id instead of $(id -g).',
    )
    parser_run_it.add_argument(
        '-n', '--container_name',
        help='Container name.',
        required=True
    )
    parser_run_it.add_argument(
        '--rm',
        help='Remove container after it stops after execution.',
        action='store_true'
    )
    parser_run_it.add_argument(
        '-w', '--workdir',
        help='Working directory inside container.'
    )
    parser_run_it.add_argument(
        'container_command',
        nargs='?'
    )

    parser_rmc = parser_cmd.add_parser(
        'rmc',
        help='Removes container.'
    )

    parser_rmi = parser_cmd.add_parser(
        'rmi',
        help='Removes image.'
    )

    parser_start = parser_cmd.add_parser(
        'start',
        help='Starts existing container.'
    )

    parser_stop = parser_cmd.add_parser(
        'stop',
        help='Stops running container.'
    )

    parser_exec = parser_cmd.add_parser(
        'exec',
        help='Executes command in a running container. Default command is bash.'
    )
    parser_exec.add_argument(
        '-w', '--workdir',
        help='Working directory inside container.'
    )
    parser_exec.add_argument(
        'container_command',
        nargs='?'
    )

    parser_info = parser_cmd.add_parser(
        'info',
        help='Prints configuration summary.'
    )

    parser_tun_make = parser_cmd.add_parser(
        'tunnels-make',
        help='Create SSH tunnels.'
    )
    parser_tun_make.add_argument('host')

    parser_tun_kill = parser_cmd.add_parser(
        'tunnels-kill',
        help='Kills SSH tunnels.'
    )
    parser_tun_kill.add_argument('host')

    return parser.parse_args()


class Command:
    regex = re.compile(r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}:([0-9]+)->')

    def __init__(self, config, dry_run=False):
        self.config = config
        self.dry_run = dry_run

    def _run(self, cmd, silent=False):
        result = None
        cmd = cmd.strip()
        if not silent:
            log(f'running:\n{cmd}')
        if not self.dry_run:
            result = run(cmd)
        if not silent:
            log('finished')
        return result

    def _taken_ports(self):
        taken_ports = set()
        ps = run('docker ps --format \'{{.Names}} {{.Ports}}\'', stdout=subprocess.PIPE)
        if ps.stdout:
            ps = ps.stdout.strip()
            for line in ps.splitlines():
                if line:
                    taken_ports.update(self.regex.findall(line))
        return taken_ports

    def _guess_ports(self):
        start_from = max(9000, int(sorted(self._taken_ports())[-1]))
        return list(map(str, range(start_from + 1, start_from + 4)))

    def _conflicting_ports(self, ports=None):
        if not ports:
            ports = [self.config.SSHD_PORT, self.config.JUPYTERLAB_PORT, self.config.TENSORBOARD_PORT]
        conflicting_ports = []
        taken_ports = self._taken_ports()
        for port in ports:
            port = port.split(':')[0]
            if port in taken_ports:
                conflicting_ports.append(port)
        return conflicting_ports

    def _check_ports(self, ports=None):
        ports = self._conflicting_ports(ports)
        if ports:
            raise RuntimeError(f'Following ports are taken: {ports}')

    def _get_ports(self, autoports, check=True):
        cfg = self.config
        if not autoports:
            if check:
                self._check_ports()
            return cfg.JUPYTERLAB_PORT, cfg.TENSORBOARD_PORT, cfg.SSHD_PORT
        else:
            jl_port, tb_port, sshd_port = self._guess_ports()
            return f'{jl_port}:8888', f'{tb_port}:6006', f'{sshd_port}:22'

    def build(self, skip_base=False, no_cache=False):
        cfg = self.config

        no_cache = '--no-cache' if no_cache else ''

        if cfg.BASE_DOCKERFILE:
            if not skip_base:
                self._run(f'''
docker build {no_cache} \\
    -f dockerfiles/{cfg.BASE_DOCKERFILE} \\
    -t {cfg.BASE_IMAGE_NAME} \\
    dockercontext
                ''')

        self._run(f'''
docker build {no_cache} \\
    -f dockerfiles/{cfg.LAB_DOCKERFILE} \\
    --build-arg DLD_BASE={cfg.BASE_IMAGE_NAME} \\
    --build-arg DLD_USER={cfg.IMAGE_USER} \\
    -t {cfg.LAB_IMAGE_NAME} \\
    dockercontext
        ''')

    def _get_group_id(self, group_name):
        return run(f'cut -d: -f3 < <(getent group {group_name})', capture_output=True)

    def run_jl(self, autoports=False, mountpoint=None, mountpoints=None, notebook_dir=None, memory=None, group=None, python_buffer=None):
        cfg = self.config
        jl_port, tb_port, sshd_port = self._get_ports(autoports)
        mountpoint = mountpoint or cfg.MOUNTPOINT
        notebook_dir = notebook_dir or cfg.NOTEBOOK_DIR
        memory = f'--memory {memory}' if memory else ''
        mountpoints = '-v ' + ' -v '.join(mountpoints) if mountpoints else ''
        group = group or '$(id -g)'
        python_buffer = python_buffer if python_buffer else 1
        self._run(f'''
nvidia-docker run \\
    -d \\
    -e DLD_UID=$(id -u) \\
    -e DLD_GID={group} \\
    -e PYTHONUNBUFFERED={python_buffer} \\
    --hostname {cfg.HOSTNAME} \\
    --name {cfg.LAB_CONTAINER_NAME} \\
    -v {mountpoint} \\
    {mountpoints} \\
    -w {cfg.WORKDIR} \\
    -p {jl_port} \\
    -p {tb_port} \\
    -p {sshd_port} \\
    --ipc host \\
    {memory} \\
    {cfg.LAB_IMAGE_NAME} \\
    jupyter lab \\
        --ip 0.0.0.0 \\
        --no-browser \\
        --notebook-dir={notebook_dir} \\
        --LabApp.token=dlservertoken
docker exec -d {cfg.LAB_CONTAINER_NAME} /usr/sbin/sshd -D
        ''')

    def run_it(self, command=None, mountpoint=None, mountpoints=None,
               memory=None, group=None, container_name=None, rm=False, workdir=None):
        cfg = self.config
        mountpoint = mountpoint or cfg.MOUNTPOINT
        mountpoints = '-v ' + ' -v '.join(mountpoints) if mountpoints else ''
        memory = f'--memory {memory}' if memory else ''
        group = group or '$(id -g)'
        container_name = f'--name {container_name}' or ''
        rm = '--rm' if rm else ''
        workdir = workdir or cfg.WORKDIR
        self._run(f'''
nvidia-docker run \\
    -it \\
    {rm} \\
    -e DLD_UID=$(id -u) \\
    -e DLD_GID={group} \\
    --hostname {cfg.HOSTNAME} \\
    {container_name} \\
    -v {mountpoint} \\
    {mountpoints} \\
    -w {workdir} \\
    --ipc host \\
    {memory} \\
    {cfg.LAB_IMAGE_NAME} \\
    {command or "bash"}
        ''')

    def start(self):
        cfg = self.config
        self._run(f'''
nvidia-docker start {cfg.LAB_CONTAINER_NAME}
docker exec -d {cfg.LAB_CONTAINER_NAME} sudo /usr/sbin/sshd -D
        ''')

    def stop(self):
        self._run(f'docker stop {self.config.LAB_CONTAINER_NAME}')

    def rmc(self):
        self._run(f'docker rm {self.config.LAB_CONTAINER_NAME}')

    def rmi(self):
        self._run(f'docker rmi {self.config.LAB_IMAGE_NAME}')

    def info(self, autoports=False):
        cfg = self.config
        jl_port, tb_port, sshd_port = self._get_ports(autoports, check=False)
        print(f'''
Base image: {cfg.BASE_IMAGE_NAME}
Lab image: {cfg.LAB_IMAGE_NAME}
Lab container: {cfg.LAB_CONTAINER_NAME}
Mountpoint: {cfg.MOUNTPOINT}
Notebook dir: {cfg.NOTEBOOK_DIR}
SSHD ports: {sshd_port}
Jupyterlab ports: {jl_port}
Tensorboard ports: {tb_port}
Conflicting ports: {', '.join(self._conflicting_ports([jl_port, tb_port, sshd_port])) or '[]'}
Taken ports: {', '.join(sorted(list(self._taken_ports())))}
        '''.strip())

    def exec(self, command=None, workdir=None):
        workdir = workdir or self.config.WORKDIR
        self._run(f'''
docker exec \\
    -w {workdir} \\
    -it {self.config.LAB_CONTAINER_NAME} sudo -u master {command or "bash"}
        ''')

    def tunnels_make(self, host, autoports=False):
        root_dir = get_script_dir()
        for name, portpair in zip(['jl', 'tb', 'ssh'], self._get_ports(autoports)):
            port = portpair.split(':')[0]
            sn = f'.tunnel-{port}-{name}'
            socket = join(root_dir, sn)
            if path.exists(socket):
                log(f'[warning]: {sn} exists')
            else:
                jl_tun = f'{port}:localhost:{port}'
                self._run(f'ssh -M -S {socket} -fNL {jl_tun} {host}', silent=True)
                log(f'[info]: created {sn}')

    def tunnels_kill(self, host, autoports=False):
        root_dir = get_script_dir()
        for name, portpair in zip(['jl', 'tb', 'ssh'], self._get_ports(autoports)):
            port = portpair.split(':')[0]
            sn = f'.tunnel-{port}-{name}'
            socket = join(root_dir, sn)
            if path.exists(socket):
                self._run(f'ssh -S {socket} -O exit {host}', silent=True)
                log(f'[info]: closed {sn}')


def get_script_dir():
    return path.dirname(path.realpath(__file__))


def change_cwd():
    # Changing current working dir to folder containing this script. Useful if a user wants to
    # run this script from arbitrary directory.
    os.chdir(get_script_dir())


def update_path(dry_run=False):
    home = run('echo $HOME', stdout=subprocess.PIPE).stdout.strip()
    for fn in os.listdir(home):
        if fn == '.bashrc' or fn == '.zshrc':
            path = f'HOME=$HOME:{get_script_dir()}'
            with open(join(home, fn), 'a') as file:
                log(f'Updating {fn}')
                log(f'Appending {path}')
                if not dry_run:
                    file.write(f'\n{path}\n')
                    file.write('export PATH\n')


def main(args):
    cmd = args.command
    if cmd == 'update-path':
        update_path(args.dry_run)
    else:
        config = process_config(importlib.import_module('configs.' + args.config), args.config)
        cmdo = Command(config, args.dry_run)
        if cmd == 'build':
            cmdo.build(args.skip_base, not args.use_cache)
        elif cmd == 'run-jl':
            cmdo.run_jl(args.autoports, args.mountpoint, args.mountpoints, args.notebook_dir, args.memory, args.group)
        elif cmd == 'run-it':
            cmdo.run_it(args.container_command, args.mountpoint, args.mountpoints,
                        args.memory, args.group, args.container_name, args.rm, args.workdir)
        elif cmd == 'start':
            cmdo.start()
        elif cmd == 'stop':
            cmdo.stop()
        elif cmd == 'rmc':
            cmdo.rmc()
        elif cmd == 'rmi':
            cmdo.rmi()
        elif cmd == 'exec':
            cmdo.exec(args.container_command, args.workdir)
        elif cmd == 'info':
            cmdo.info(args.autoports)
        elif cmd == 'tunnels-make':
            cmdo.tunnels_make(args.host, args.autoports)
        elif cmd == 'tunnels-kill':
            cmdo.tunnels_kill(args.host, args.autoports)


if __name__ == '__main__':
    change_cwd()
    main(parse_args())
