#!/usr/bin/env python
# -*- coding: utf-8 -*-#

from uuid import uuid4
from datetime import datetime, timedelta

from fuzzywuzzy import fuzz


class TaskSolverException(Exception):
    pass


class Task(object):
    """
    Tasks are supposed to be solved by players, the logic here is that if a task is solved (a)
    destination waypoint(s) or dialog interaction(s) will become available.
    """
    def __init__(self,
                 destination,
                 description: str,
                 text: str,
                 solution=None,
                 media=None,
                 items=None,
                 time_limit: float = 0.0,
                 money_limit: float = 0.0,
                 budget_modification: float = 0.0,
                 ratio: int = 90,
                 days: int = 1,
                 offset: float = 0.01):
        """
        each task can have varying solution types; text, date, image, etc.
        :param destination: destination (waypoint or interaction) that becomes available on completing the task
        :param description: description text used for referencing
        :param text: text describing the task
        :param solution: solution that solves the task
        :param media: optional media for the task (img, vid, etc.)
        :param items: inventory items to be added after a task is completed
        :param time_limit: amount of time to solve the task (in seconds)
        :param money_limit: amount of money needed in order to access the task
        :param budget_modification: modify budget on completing task
        :param ratio: fuzzyness ratio lower bound for text answers
        :param days: timedelta allowed on date answers
        :param offset: delta allowed for float answers
        """
        self.id = uuid4()
        self.destination = destination
        self.description = description
        self.text = text
        self.solution = solution
        self.media = media
        self.items = items
        self.time_limit = time_limit
        self.money_limit = money_limit
        self.budget_modification = budget_modification
        self.ratio = ratio
        self.days = days
        self.offset = offset

    def __eq__(self, other):
        if self and other and isinstance(other, Task):
            return self.id == other.id
        return False

    def __hash__(self):
        return self.id.__hash__()

    def __str__(self):
        return self.description

    def __repr__(self):
        return f'Task: ({self.description})'

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
