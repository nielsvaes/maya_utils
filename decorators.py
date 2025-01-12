from utils import lists
import pymel.core as pm

class progress_window(object):
    def __init__(self, title="Working...", status="Working...", start=0, wide=True):
        """
        Use this decorator to easily show a progress window
        Adapted from #http://josbalcaen.com/maya-python-progress-decorator/

        Example use:

        @progress_window_decorator()
        def make_spheres(amount=25):
            for i in range(amount):
                pm.polySphere()
                time.sleep(0.1)

                # this is where we update the decorator
                make_spheres.update_progress(100/amount, "Making sphere #%s" % i)


        make_spheres()


        :param status: <string> update message
        :param start: <int> where to start, usually best to leave this at 0
        :param wide: <bool> makes the window bigger because it looks cooler!

        """
        self.start_value = start
        self.end_value = 100
        self.status = status
        self.step_value = 0
        self.title = title

        if wide:
            self.status += " " * 500

        # kill any existing progress windows
        pm.progressWindow(endProgress=True)

    def update_progress(self, step_update=1, status=""):
        if status == "":
            status = self.status

        self.step_value += step_update
        pm.progressWindow(edit=True, progress=self.step_value, status=status)

    def start(self):
        pm.progressWindow(title=self.title, progress=1,
                          status=self.status,
                          maxValue=self.end_value,
                          isInterruptable=False)

    def end(self):
        pm.progressWindow(endProgress=True)
        self.step_value = 0


    def __call__(self, in_function):
        def wrapped_f(*args, **kwargs):
            # Start progress
            self.start()
            # Call original function
            result = in_function(*args, **kwargs)
            # End progress
            self.end()
            # return original function result
            return result

        # Add special methods to the wrapped function
        wrapped_f.update_progress = self.update_progress

        # Copy over attributes
        wrapped_f.__doc__ = in_function.__doc__
        wrapped_f.__name__ = in_function.__name__
        wrapped_f.__module__ = in_function.__module__

        # Return wrapped function
        return wrapped_f

def clear_selection(method):
    def wrapper(*args, **kwargs):
        pm.select(None)
        method(*args, **kwargs)

    return wrapper

def deselect_reselect(method):
    def wrapper(*args, **kwargs):
        selection = pm.selected()
        pm.select(None)
        method(*args, **kwargs)
        pm.select(selection)

    return wrapper


class ListNewNodes(object):
    def __init__(self, *args, **kwargs):
        self.existing_nodes = None
        self.ls_args = args
        self.ls_kwargs = kwargs

        self.result = None

    def __enter__(self, *args, **kwargs):
        self.existing_nodes = pm.ls(*self.ls_args, **self.ls_kwargs)
        return self

    def __exit__(self, *args, **kwargs):
        post_scene_nodes = pm.ls(*self.ls_args, **self.ls_kwargs)

        # figure out which nodes have been created
        new_nodes = lists.difference([self.existing_nodes, post_scene_nodes])

        # remove pymel undo nodes that might end up in the list
        for new_node in new_nodes:
            if "__pymelUndoNode" in new_node.name():
                new_nodes.remove(new_node)

        self.result = new_nodes
