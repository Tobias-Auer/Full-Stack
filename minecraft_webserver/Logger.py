import logging
import sys


def logger():
    logger_var = logging.getLogger()
    logger_var.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s', '%m-%d-%Y %H:%M:%S')

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.INFO)
    stdout_handler.setFormatter(formatter)

    file_handler = logging.FileHandler('logs.log')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    logger_var.addHandler(file_handler)
    logger_var.addHandler(stdout_handler)
    return logger_var
