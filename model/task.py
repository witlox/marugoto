#!/usr/bin/env python
# -*- coding: utf-8 -*-#


class Task(object):
    """
    Tasks are supposed to be solved by players, the logic here is that if a task is solved (a)
    destination waypoint(s) will become available.
    """
    def __init__(self, description, media=None):
        self.description = description
        self.media = media


class TextTask(Task):
    def __init__(self, description, solution, media=None):
        super().__init__(description, media)
        self.solution = solution


class DateTask(Task):
    def __init__(self, description, solution, media=None):
        super().__init__(description, media)
        self.solution = solution


class ChoiceTask(Task):
    def __init__(self, description, solution, media=None):
        super().__init__(description, media)
        self.solution = solution


class MultipleChoiceTask(Task):
    """
    Each combination of multiple choice answers that points to a (single) waypoint needs to be defined.
    """
    def __init__(self, description, solution, media=None):
        super().__init__(description, media)
        self.solution = solution


class UploadTask(Task):
    def __init__(self, description, solution, media=None):
        super().__init__(description, media)
        self.solution = solution
