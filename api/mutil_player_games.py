#!/usr/bin/env python
# -*- coding: utf-8 -*-#

import logging

from connexion import NoContent
from flask import session
# from sqlalchemy.exc import SQLAlchemyError
#
# from api.admin import is_admin, is_group_admin
# from db.group import Member, Group
# from db.handler import db_session
# from db.user import User

logger = logging.getLogger('api.group')


def get_groups(active=False):
    """
    list all groups (admins only)
    :param active: only show active groups
    :return: list of group
    """
    if not is_admin():
        return NoContent, 401
    if active:
        groups = [g.dump() for g in db_session.query(Group).all() if g.active]
    else:
        groups = [g.dump() for g in db_session.query(Group).all()]
    return groups, 200


def add_group(g):
    """
    add a group (admins only)
    :param g: group
    :return: group
    """
    if not is_admin():
        return NoContent, 401
    u = db_session.query(User).filter(User.dom_name == g['dom_name']).one_or_none()
    if not u:
        return "could not find user {0} for ownership".format(g['dom_name']), 404
    g.pop('dom_name', None)
    try:
        g = Group(**g, user_id=u.id)
        db_session.add(g)
        db_session.commit()
        db_session.refresh(g)
        return g.dump(), 201
    except SQLAlchemyError:
        logger.exception("error while creating group")
        return NoContent, 500


def update_group(gid, g):
    """
    update a group (admins and group admins)
    :param gid: group id
    :param g: group
    :return: success or fail
    """
    if not is_group_admin(gid):
        return NoContent, 401
    group = db_session.query(Group).filter(Group.id == gid).one_or_none()
    group.pop('id', None)
    try:
        for k in g:
            setattr(group, k, g[k])
        db_session.commit()
        return NoContent, 200
    except SQLAlchemyError:
        logger.exception("error while updating group")
        return NoContent, 500


def get_group_users(gid):
    """
    get users of a group (admins, group admins and members)
    :param gid: group id
    :return: list of user
    """
    if not is_admin():
        u = None
        if 'username' in session:
            u = db_session.query(User).filter(User.dom_name == session['username']).one_or_none()
        if not u or not db_session.query(Member).filter(Member.group_id == gid and Member.user_id == u.id).one_or_none():
            logger.warning("user {0} not found as part of group".format(session['username']))
            return NoContent, 401
    users = []
    for group_user in db_session.query(Member).filter(Member.group_id == gid).all():
        gu = db_session.query(User).filter(User.id == group_user.user_id).one_or_none()
        if gu:
            users.append(dict(dom_name=gu.dom_name, full_name=gu.full_name, admin=group_user.admin))
    return users, 200


def add_group_user(gid, u, admin):
    """
    add user to group (admins and group admins)
    :param gid: group id
    :param u: dom_name
    :param admin: add as admin
    :return:
    """
    if not is_group_admin(gid):
        return NoContent, 401
    u = db_session.query(User).filter(User.dom_name == u).one_or_none()
    if not u:
        return 'User does not exist', 404
    group = db_session.query(Group).filter(Group.id == gid).one()
    try:
        db_session.add(Member(group=group, user=u, admin=admin))
        db_session.commit()
        return NoContent, 201
    except SQLAlchemyError:
        logger.exception("error while updating group")
        return NoContent, 500


def remove_group_user(gid, u):
    """
    remove user from group (admins and group admins)
    :param gid: group id
    :param u: dom_name
    :return: success or failure
    """
    if not is_group_admin(gid):
        return NoContent, 401
    u = db_session.query(User).filter(User.dom_name == u).one_or_none()
    if not u:
        return 'User does not exist', 404
    group = db_session.query(Group).filter(Group.id == gid).one()
    try:
        db_session.query(Member).filter(Member.group == group and Member.user == u).delete()
        db_session.commit()
        return NoContent, 200
    except SQLAlchemyError:
        logger.exception("error while updating group")
        return NoContent, 500
