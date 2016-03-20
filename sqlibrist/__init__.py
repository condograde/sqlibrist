# -*- coding: utf8 -*-
VERSION = '0.0.6'


from sqlibrist.helpers import SqlibristException, handle_exception, \
    get_command_parser


def main():
    parser = get_command_parser()
    args = parser.parse_args()

    try:
        args.func(args)
    except SqlibristException as e:
        handle_exception(e)


if __name__ == '__main__':
    main()