#!/usr/bin/env python
# -*- coding: utf-8 -*-#

import logging

from connexion import NoContent
from flask import session
from sqlalchemy.exc import SQLAlchemyError

from api.admin import is_admin
from db.group import Member, Group
from db.handler import db_session
from db.player import User


logger = logging.getLogger('api.user')


def get_user_with_groups(uid):
    """
    get user by id with groups
    :param uid: user id
    :return: user with groups
    """
    u = db_session.query(User)
    user = u.filter(User.id == uid).one_or_none()
    if not user:
        logger.warning("user with id {0} not found".format(uid))
        return None
    user = user.dump()
    user['groups'] = []
    for member in db_session.query(Member).filter(Member.user_id == uid).all():
        group = db_session.query(Group).filter(Group.id == member.group_id).one().dump()
        user['groups'].append(group)
    return user


def get_users():
    """
    get all users (admins)
    :return: list of user
    """
    if not is_admin():
        return NoContent, 401
    return [get_user_with_groups(u.id) for u in db_session.query(User).all() if u]


def add_user(u):
    """
    add new user
    :param u: user
    :return: user
    """
    if not is_admin():
        return NoContent, 401
    if 'admin' == u['dom_name']:
        logger.error("cannot add user admin, this name is reserved")
        return NoContent, 500
    u = User(**u)
    try:
        db_session.add(u)
        db_session.commit()
        db_session.refresh(u)
        return u.dump(), 201
    except SQLAlchemyError:
        logger.exception("error while creating account")
        return NoContent, 500


def remove_user(name):
    """
    remove existing user
    :param name: user
    :return: success or failure
    """
    if not is_admin():
        return NoContent, 401
    try:
        db_session.query(User).filter(User.dom_name == name).delete()
        db_session.commit()
        return NoContent, 200
    except SQLAlchemyError:
        logger.exception("error while creating account")
        return NoContent, 500


def get_user(uid):
    """
    get user
    :param uid: user id
    :return: user (with groups)
    """
    if not is_admin():
        return NoContent, 401
    return get_user_with_groups(uid), 200


def find_user(name):
    """
    find user by name
    :param name: user name
    :return: user with groups
    """
    if is_admin():
        u = db_session.query(User).filter(User.dom_name == name).one_or_none()
        if not u:
            logger.warning("user with name {0} not found".format(name))
            return NoContent, 404
        return get_user_with_groups(u.id), 200
    if 'username' in session:
        user = db_session.query(User).filter(User.dom_name == session['username']).one_or_none()
        if not user:
            return NoContent, 401
        u = db_session.query(User).filter(User.dom_name == name).one_or_none()
        if not u:
            return NoContent, 401
        for admin in db_session.query(Member).filter(Member.user_id == user.id and Member.admin).all():
            if db_session.query(Member).filter(Member.group_id == admin.group_id and Member.user_id == u.id).one_or_none():
                return get_user_with_groups(u.id), 200
        return NoContent, 401
    return NoContent, 401


def get_myself():
    """
    get your own info
    :return: yourself and your groups
    """
    if 'username' not in session:
        return NoContent, 500
    u = db_session.query(User).filter(User.dom_name == session['username']).one_or_none()
    if not u:
        logger.error("session user {0} not in database".format(session['username']))
        return NoContent, 500
    return get_user_with_groups(u.id), 200
