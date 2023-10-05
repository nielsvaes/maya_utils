import pymel.core as pm

FPS_TO_STRING = {
    30: "ntsc",
    60: "ntscf",
}

STRING_TO_FPS = {
    "ntsc": 30,
    "ntscf": 60
}


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
    pm.playbackOptions(minTime=start, maxTime=end, animationStartTime=start, animationEndTime=end)

def get_selected_time_range():
    """
    Gets the selected timeline range.

    :return: *list* The currently active/selected timerange
    """
    playbackslider = pm.melGlobals["gPlayBackSlider"]

    sel_time_range = pm.timeControl(playbackslider, q=True, rangeArray=True)
    sel_time_range[-1] = sel_time_range[-1] - 1

    if sel_time_range[1] - sel_time_range[0] == 0:
        sel_time_range = [sel_time_range[0], sel_time_range[0]]

    return sel_time_range

def get_time_bookmarks_data():
    all_bookmark_data = {}
    for node in pm.ls(type="timeSliderBookmark"):
        bookmark_data = {}

        for interesting_attr in ["name", "timeRangeStart", "timeRangeStop", "colorR", "colorG", "colorB", "exportable", "clip_type"]:
            if node.hasAttr(interesting_attr):
                bookmark_data[interesting_attr] = node.getAttr(interesting_attr)

        all_bookmark_data[node.name()] = bookmark_data

    return all_bookmark_data

def get_fps():
    """
    Returns the current FPS

    :return: *float*
    """
    return STRING_TO_FPS.get(pm.currentUnit(query=True, time=True))

def set_fps(fps_number):
    """
    Set the current FPS

    :return: *float*
    """
    pm.currentUnit(time=FPS_TO_STRING.get(fps_number))
