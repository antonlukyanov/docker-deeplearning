BASE_DOCKERFILE = 'Deepo-py37-cu10'
BASE_IMAGE_SUFFIX = '-deeppavlov'

IMAGE_PREFIX = 'lukyanov'
LAB_DOCKERFILE = 'Lab-deeppavlov'
LAB_IMAGE_SUFFIX = BASE_IMAGE_SUFFIX
JUPYTERLAB_PORT = '9103:8888'
TENSORBOARD_PORT = '9104:6006'
SSHD_PORT = '9105:22'
WORKDIR = '/workspace/projects/deeppavlov'
