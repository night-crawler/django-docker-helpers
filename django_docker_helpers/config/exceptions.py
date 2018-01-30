class KVStorageKeyDoestNotExist(KeyError):
    pass


class KVStorageValueDoestNotExist(ValueError):
    pass


class RequiredValueIsEmpty(ValueError):
    pass
