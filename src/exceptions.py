class invalidRegionException(Exception):
     def __init__(self, msg='ERROR! Invalid Region.', *args, **kwargs):
        super().__init__(msg, *args, **kwargs)


class emptyTrackListException(Exception):
     def __init__(self, msg='ERROR! Track list is empty.', *args, **kwargs):
        super().__init__(msg, *args, **kwargs)