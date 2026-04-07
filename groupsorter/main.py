"""Entry point for GroupSorter."""


def main() -> None:
    from .gui import App

    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
