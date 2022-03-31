import pymel.core as pm

def get_time_range():
    """
    Returns begin and end frame

    :return: *list*
    """
    start_time = int(pm.playbackOptions(q=True, min=True))
    end_time = int(pm.playbackOptions(q=True, max=True))
    return start_time, end_time


def set_time_range(start, end):
    """
    Because no getter can do without a setter

    :param start: *int* start time
    :param end: *int* end time
    :return: None
    """
    pm.playbackOptions(minTime=start, maxTime=end)

