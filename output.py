import curses
import logging
import utility
import html
import wcwidth

COLOR_PAIR_GREEN = 1
COLOR_PAIR_YELLOW = 2
COLOR_PAIR_PURPLE = 3
COLOR_PAIR_RED = 4
COLOR_PAIR_BLUE = 5

def bound_addstr(window, string, color_pair = -1):
    max_y, max_x = window.getmaxyx()
    current_y, current_x = window.getyx()
    y, x = max(1, current_y), max(1, current_x)

    for ch in string:
        if ch == "\n" or x >= max_x - 1:
            y += 1
            x = 1
            if y >= max_y - 1:
                window.scroll(1)
                y = max_y - 2
            continue
        if color_pair == -1:
            window.addch(y, x, ch)
        else:
            window.addch(y, x, ch, color_pair)
        x += max(wcwidth.wcwidth(ch), 1)
    window.move(y, x)

class Output(logging.Handler):
    def __init__(self, basic):
        super().__init__()
        self.basic = basic
        self.monitor_status = {}
        self.initialize()

    def initialize(self):
        # Basic mode means we can't have windows.
        if self.basic:
            return

        self.initialize_curses()

        height, width = self.stdscr.getmaxyx() # why is it backwards?

        # vertical split size
        left_width = width // 2
        right_width = width - left_width

        # horizontal split in the right pane
        right_top_height = height // 2
        right_bottom_height = height - right_top_height

        # create window
        self.illust_window = curses.newwin(height, left_width, 0, 0)
        self.status_window = curses.newwin(right_top_height, right_width, 0, left_width)
        self.log_window = curses.newwin(right_bottom_height, right_width, right_top_height, left_width)

        self.illust_window.box()
        self.status_window.box()
        self.log_window.box()

        self.illust_window.scrollok(True)
        self.log_window.scrollok(True)

        self.illust_window.refresh()
        self.status_window.refresh()
        self.log_window.refresh()

        self.initialize_colors()

    def initialize_curses(self):
        self.stdscr = curses.initscr()
        curses.start_color()
        curses.use_default_colors()
        curses.noecho()
        curses.cbreak()
        self.stdscr.keypad(True)

        self.stdscr.clear()
        curses.curs_set(0)

    def initialize_colors(self):
        curses.init_pair(COLOR_PAIR_GREEN, curses.COLOR_GREEN, -1)
        curses.init_pair(COLOR_PAIR_YELLOW, curses.COLOR_YELLOW, -1)
        curses.init_pair(COLOR_PAIR_PURPLE, curses.COLOR_MAGENTA, -1)
        curses.init_pair(COLOR_PAIR_RED, curses.COLOR_RED, -1)
        curses.init_pair(COLOR_PAIR_BLUE, curses.COLOR_CYAN, -1)

    def deinitialize(self):
        if not self.basic:
            self.stdscr.keypad(False)
            curses.echo()
            curses.nocbreak()
            curses.endwin()

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

    def print_illust_curses(self, illust, unescape_caption, multiline_caption, newline):
        try:
            # TODO Figure out a way to put links
            # Curses has built-in mouse support (if the terminal supports it)
            # so maybe that can be used. idk.
            # Low priority because I don't really click the links anymore. But
            # it'd be nice.

            bound_addstr(self.illust_window, f"[{utility.hrdatetime()}] ")
            bound_addstr(self.illust_window, f"Found new illustration:\n", curses.color_pair(COLOR_PAIR_GREEN))
            bound_addstr(self.illust_window, f"pixiv #{illust.iden}")
            if illust.page_count != 0:
                bound_addstr(self.illust_window, f" ({illust.page_count} pages)", curses.color_pair(COLOR_PAIR_YELLOW))
            if illust.is_sensitive:
                bound_addstr(self.illust_window, f" (sensitive content)", curses.color_pair(COLOR_PAIR_PURPLE))
            bound_addstr(self.illust_window, "\n")
            if illust.is_ai:
                bound_addstr(self.illust_window, "[!] AI-generated [!]\n", curses.color_pair(COLOR_PAIR_RED))
            bound_addstr(self.illust_window, "Title: ")
            bound_addstr(self.illust_window, illust.title, curses.color_pair(COLOR_PAIR_BLUE))
            bound_addstr(self.illust_window, f"\nCaption: {newline}")
            bound_addstr(self.illust_window, f"{multiline_caption}\n", curses.color_pair(COLOR_PAIR_BLUE))
            bound_addstr(self.illust_window, "Artist: ")
            bound_addstr(self.illust_window, illust.user.name, curses.color_pair(COLOR_PAIR_BLUE))
            bound_addstr(self.illust_window, f" (@{illust.user.account})\nTags: ")
            last_tag_index = len(illust.tags) - 1
            
            # Does what str(tag) does, but adjusted for curses output.
            for i, tag in enumerate(illust.tags):
                if tag.translated_name is None:
                    if tag.name == "R-18" or tag.name == "R-18G":
                        bound_addstr(self.illust_window, tag.name, curses.color_pair(COLOR_PAIR_RED))
                    else:
                        bound_addstr(self.illust_window, tag.name, curses.color_pair(COLOR_PAIR_BLUE))
                else:
                    bound_addstr(self.illust_window, f"{tag.name} / {tag.translated_name}", curses.color_pair(COLOR_PAIR_BLUE))
                if i != last_tag_index:
                    bound_addstr(self.illust_window, ", ")
            bound_addstr(self.illust_window, "\n\n")

            draw_window_box(self.illust_window)
            self.illust_window.refresh()
        except Exception as exc:
            logging.getLogger().error(f"Error when printing illustration: %s", exc)

    def print_illust(self, illust):
        unescape_caption = html.unescape(illust.caption)
        multiline_caption = unescape_caption.replace("<br />", "\n")
        newline = "\n" if multiline_caption != unescape_caption else ""

        if self.basic:
            self.print_illust_basic(illust, unescape_caption, multiline_caption, newline)
        else:
            self.print_illust_curses(illust, unescape_caption, multiline_caption, newline)

    def update_status(self, monitor_index, left, total):
        if self.basic:
            return # Status window is not available with basic output

        self.monitor_status[monitor_index] = left, total
        self.status_window.clear()
        self.status_window.move(1, 1)

        bound_addstr(self.status_window, "pixiv-monitor\n")
        for index in self.monitor_status:
            monitor_left = self.monitor_status[index][0]
            monitor_total = self.monitor_status[index][1]
            bound_addstr(self.status_window, f"Monitor #{index + 1}: ")
            bound_addstr(self.status_window, f"{monitor_left}/{monitor_total} pending\n", curses.color_pair(COLOR_PAIR_BLUE))

        self.status_window.refresh()

    def emit(self, record):
        if self.basic:
            return # Outputting to file already covered by logger's file handler

        try:
            message = self.format(record)
            bound_addstr(self.log_window, f"{message}\n")
            self.log_window.refresh()
        except Exception:
            self.handleError(record)
