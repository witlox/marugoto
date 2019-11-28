#!/usr/bin/env python
# -*- coding: utf-8 -*-#

from datetime import datetime, timedelta

from fuzzywuzzy import fuzz


class TaskSolverException(Exception):
    pass


class Task(object):
    """
    Tasks are supposed to be solved by players, the logic here is that if a task is solved (a)
    destination waypoint(s) or dialog interaction(s) will become available.
    """
    def __init__(self, description: str, text: str, solution=None, media=None, ratio=90, days=1, offset=0.01):
        """
        each task can have varying solution types; text, date, image, etc.
        :param description: description text used for referencing
        :param text: text describing the task
        :param solution: solution that solves the task
        :param media: optional media for the task (img, vid, etc.)
        :param ratio: fuzzyness ratio lower bound for text answers
        :param days: timedelta allowed on date answers
        :param offset: delta allowed for float answers
        """
        self.description = description
        self.text = text
        self.solution = solution
        self.media = media
        self.ratio = ratio
        self.days = days
        self.offset = offset

    def solve(self, answer) -> bool:
        """
        try to solve the task with a given answer, if no solution has been given it will always return True
        :param answer: any answer of any type
        :return: success or fail
        """
        if not self.solution:
            return True
        if not answer:
            return False
        if not isinstance(answer, type(self.solution)):
            return False
        if isinstance(answer, str):
            return fuzz.partial_ratio(answer, self.solution) > self.ratio
        if isinstance(answer, datetime):
            return answer - self.solution < timedelta(days=self.days)
        if isinstance(answer, list):
            return self.solution.sort() == answer.sort()
        if isinstance(answer, int):
            return self.solution == answer
        if isinstance(answer, float):
            return self.solution - answer < self.offset
        if isinstance(answer, bool):
            return self.solution == answer
        raise TaskSolverException(f'could not find solver for type {type(answer)} ({self.description})')
