import urwid
import logging
import utility
import html
import queue
import threading

class Output(logging.Handler):
    def __init__(self, basic):
        super().__init__()
        self.basic = basic
        self.monitor_status = {}
        self.advanced_initialized = False

    def initialize(self):
        # Basic mode means we can't have windows.
        if self.basic:
            return

        self.PALETTE = [
            ('green', 'dark green', ''),
            ('yellow', 'yellow', ''),
            ('purple', 'dark magenta', ''),
            ('red', 'dark red', ''),
            ('blue', 'dark cyan', ''),
            ('header', 'white', 'dark blue'),
            ('footer', 'white', 'dark gray')
        ]

        self.illust_list_walker = urwid.SimpleListWalker([])
        self.illust_list_box = urwid.ListBox(self.illust_list_walker)

        self.status_text = urwid.Text("pixiv-monitor\n", align="left")
        self.status_box = urwid.LineBox(self.status_text, title="pixiv-monitor")

        self.log_list_walker = urwid.SimpleListWalker([])
        self.log_list_box = urwid.ListBox(self.log_list_walker)
        self.log_box = urwid.LineBox(self.log_list_box, title="log")

        self.right_pane = urwid.Pile([
            ("weight", 1, self.status_box),
            ("weight", 2, self.log_box)
        ])

        self.layout = urwid.Columns([
            ("weight", 2, urwid.LineBox(self.illust_list_box)),
            ("weight", 1, self.right_pane)
        ])

        logging.getLogger("urwid").setLevel(logging.INFO)

        self.loop = urwid.MainLoop(self.layout, self.PALETTE, unhandled_input=self.handle_input)
        self.advanced_initialized = True
    
    def run_loop(self):
        if not self.basic:
            self.loop.run()

    def handle_input(self, key):
        if key in ("ctrl c", "q"):
            raise urwid.ExitMainLoop()
        return key

    def print_illust_basic(self, illust, unescape_caption, multiline_caption, newline):
        caption_string = f"Caption: \033[0;36m{newline}{multiline_caption}\033[0m\n" if len(illust.caption.strip()) != 0 else ""
        ai_string = "" if not illust.is_ai else "\033[0;31m[!] AI-generated [!]\033[0m\n"

        page_count_string = "" if illust.page_count == 0 else f" \033[0;33m({illust.page_count} pages)\033[0m"
        sensitive_string = "" if not illust.is_sensitive else f" \033[0;35m(sensitive content)\033[0m"

        print(
            f"[{utility.hrdatetime()}] \033[0;32mFound new illustration:\033[0m\n"
            f"\033]8;;{illust.pixiv_link()}\033\\pixiv #{illust.iden}\033]8;;\033\\{page_count_string}{sensitive_string}\n"
            f"{ai_string}"
            f"Title: \033[0;36m{illust.title}\033[0m\n"
            f"{caption_string}"
            f"Artist: \033[0;36m\033]8;;{illust.user.pixiv_link()}\033\\{illust.user.name}\033]8;;\033\\\033[0m \033]8;;{illust.user.pixiv_stacc_link()}\033\\(@{illust.user.account})\033]8;;\033\\\n"
            f"Tags: {illust.get_tag_string()}\n"
        )

    def print_illust_advanced(self, illust, unescape_caption, multiline_caption, newline):
        try:
            # TODO does urwid support links? i'm too tired atm to find out

            lines = []
            lines.append(('green', f"[{utility.hrdatetime()}] Found new illustration:\n"))
            lines.append(f"pixiv #{illust.iden}")
            if illust.page_count:
                lines.append(('yellow', f" ({illust.page_count} pages)"))
            if illust.is_sensitive:
                lines.append(('purple', " (sensitive content)"))
            lines.append('\n')
            if illust.is_ai:
                lines.append(('red', "[!] AI-generated [!]\n"))
            lines.append("Title: ")
            lines.append(('blue', f"{illust.title}\n"))
            lines.append(f"Caption: {newline}")
            lines.append(('blue', f"{multiline_caption}\n"))
            lines.append("Artist: ")
            lines.append(('blue', f"{illust.user.name} (@{illust.user.account})\n"))
            lines.append("Tags: ")

            last_tag_index = len(illust.tags) - 1
            for i, tag in enumerate(illust.tags):
                if tag.translated_name is None:
                    color = 'red' if tag.name in ('R-18', 'R-18G') else 'blue'
                    lines.append((color, tag.name))
                else:
                    lines.append(('blue', f"{tag.name} / {tag.translated_name}"))
                if i != last_tag_index:
                    lines.append(", ")
            lines.append("\n\n")

            self.illust_list_walker.append(urwid.Text(lines))
            self.illust_list_box.set_focus(len(self.illust_list_walker) - 1)
            self.loop.draw_screen()
        except Exception as exc:
            logging.getLogger().error(f"Error when printing illustration: %s", exc)

    def print_illust(self, illust):
        unescape_caption = html.unescape(illust.caption)
        multiline_caption = unescape_caption.replace("<br />", "\n")
        newline = "\n" if multiline_caption != unescape_caption else ""

        if self.basic or not self.advanced_initialized:
            self.print_illust_basic(illust, unescape_caption, multiline_caption, newline)
        else:
            self.print_illust_advanced(illust, unescape_caption, multiline_caption, newline)

    def update_status(self, monitor_index, left, total):
        if self.basic or not self.advanced_initialized:
            return # Status window is not available with basic output

        self.monitor_status[monitor_index] = (left, total)
        lines = []
        for index, (l, t) in self.monitor_status.items():
            lines.append(f"Monitor #{index + 1}: ")
            lines.append(('blue', f"{l}/{t} pending\n"))
        self.status_text.set_text(lines)
        self.loop.draw_screen()

    def emit(self, record):
        if self.basic or not self.advanced_initialized:
            return # Outputting to file already covered by logger's file handler. Also we can't log to advanced UI if it's not initialized.

        try:
            message = self.format(record)
            self.log_list_walker.append(urwid.Text(message))
            self.log_list_box.set_focus(len(self.log_list_walker) - 1)
            self.loop.draw_screen()
        except Exception:
            self.handleError(record)
