from functools import lru_cache

from libcloud.storage.providers import get_driver
from libcloud.storage.types import ContainerAlreadyExistsError
from libcloud.storage.types import ObjectError
from libcloud.storage.types import Provider

from faceanalysis.log import get_logger
from faceanalysis.settings import ALLOWED_EXTENSIONS
from faceanalysis.settings import STORAGE_PROVIDER
from faceanalysis.settings import STORAGE_KEY
from faceanalysis.settings import STORAGE_SECRET
from faceanalysis.settings import STORAGE_CONTAINER


logger = get_logger(__name__)


class StorageError(Exception):
    pass


@lru_cache(maxsize=1)
def _get_storage_service():
    driver_class = get_driver(getattr(Provider, STORAGE_PROVIDER))
    storage_driver = driver_class(STORAGE_KEY, STORAGE_SECRET)
    try:
        storage_container = storage_driver.create_container(STORAGE_CONTAINER)
    except ContainerAlreadyExistsError:
        storage_container = storage_driver.get_container(STORAGE_CONTAINER)
    return storage_container


def _get_image(img_id):
    container = _get_storage_service()
    for extension in ALLOWED_EXTENSIONS:
        image_name = '{}.{}'.format(img_id, extension)
        try:
            image = container.get_object(image_name)
        except ObjectError:
            continue
        else:
            return image

    raise StorageError('Image {} does not exist'.format(img_id))


def store_image(iterator, image_name):
    container = _get_storage_service()
    try:
        container.upload_object_via_stream(iterator, image_name)
    except (ObjectError, OSError) as ex:
        raise StorageError('Unable to store {}'.format(image_name)) from ex

    logger.debug('Stored image %s', image_name)


def delete_image(img_id):
    image = _get_image(img_id)

    if not image.delete():
        raise StorageError('Unable to delete image {}'.format(img_id))

    logger.debug('Removed image %s', img_id)


def get_image_path(img_id):
    image = _get_image(img_id)
    return image.get_cdn_url()
