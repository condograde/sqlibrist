# -*- coding: utf8 -*-
VERSION = '0.1.0'

from sqlibrist.helpers import SqlibristException, handle_exception, \
    get_command_parser, get_config


def main():
    parser = get_command_parser()
    args = parser.parse_args()
    config = get_config(args)
    try:
        args.func(args, config)
    except SqlibristException as e:
        handle_exception(e)


if __name__ == '__main__':
    main()
