class KVStorageKeyDoestNotExist(KeyError):
    pass


class KVStorageValueIsEmpty(ValueError):
    pass


class RequiredValueIsEmpty(ValueError):
    pass
