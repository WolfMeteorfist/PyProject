from watchdog.events import FileSystemEventHandler


class EventHandler(FileSystemEventHandler):
    event_dcit: dict[str, int] = dict()

    def __init__(self, func) -> None:
        super().__init__()
        self.func = func

    def on_modified(self, event):
        if event.is_directory:
            return

        filename = event.src_path

        if filename not in self.event_dcit:
            self.event_dcit[filename] = 0

        if self.event_dcit[filename] == 0:
            f = open(event.src_path, 'a')
            self.func(f)
            print(f'event type: {event.event_type} path : {event.src_path}')
            self.event_dcit[filename] += 1
        elif self.event_dcit[filename] == 1:
            self.event_dcit[filename] = 0
