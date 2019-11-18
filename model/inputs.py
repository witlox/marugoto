#!/usr/bin/env python
# -*- coding: utf-8 -*-#

from datetime import datetime

from model.task import TextTask, DateTask, ChoiceTask, MultipleChoiceTask, UploadTask


class Input(object):
    def __init__(self, waypoint):
        """
        Input for a given waypoint task at specific UTC
        :param waypoint: waypoint associated with input
        """
        self.at = datetime.utcnow()
        self.waypoint = waypoint
        self.input_association = None
        self.answer = None


class TextInput(Input):
    def __init__(self, waypoint, text):
        super().__init__(waypoint)
        self.input_association = TextTask
        self.answer = text


class DateInput(Input):
    def __init__(self, waypoint, date):
        super().__init__(waypoint)
        self.input_association = DateTask
        self.answer = date


class ChoiceInput(Input):
    def __init__(self, waypoint, choice):
        super().__init__(waypoint)
        self.input_association = ChoiceTask
        self.answer = choice


class MultipleChoiceInput(Input):
    def __init__(self, waypoint, choices):
        super().__init__(waypoint)
        self.input_association = MultipleChoiceTask
        self.answer = choices


class UploadInput(Input):
    def __init__(self, waypoint, file):
        super().__init__(waypoint)
        self.input_association = UploadTask
        self.answer = file
