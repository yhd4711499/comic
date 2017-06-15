import os


def clear_screen():
    _ = os.system({
                      'nt': 'cls',
                      'posix': 'clear'
                  }[os.name])


class Context(object):
    """docstring for Context"""

    def __init__(self):
        pass


class Stage:
    def __init__(self, name):
        self.name = name
        self.input = None
        self.ctx = None

    def enter(self, ctx):
        self.ctx = ctx
        clear_screen()
        self.on_enter()
        self.on_resume()
        while True:
            self.on_turn_started()
            if self.should_leave():
                break
            else:
                try:
                    self.on_response()
                except KeyboardInterrupt:
                    print("operation cancelled.")
                    break
            self.on_turn_stopped()
        self.on_pause()
        self.on_leave()
        clear_screen()

    def should_leave(self):
        return False

    def change(self, stage):
        self.on_pause()
        stage.enter(self.ctx)
        self.on_resume()

    def on_enter(self):
        pass

    def on_resume(self):
        pass

    def on_turn_started(self):
        pass

    def on_turn_stopped(self):
        pass

    def on_pause(self):
        pass

    def on_leave(self):
        pass

    def on_response(self):
        pass
