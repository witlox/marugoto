#!/usr/bin/env python
# -*- coding: utf-8 -*-#

import logging
import hashlib
import sys
from time import time

from connexion import NoContent
from flask import session

logger = logging.getLogger('api.auth')
tokens = {}


def generate_token(identifier):
    """
    generate a JWT token
    :param identifier: name of user or service
    :return: JWT token
    """
    timestamp = int(time())
    payload = {
        "iss": config.token().get('issuer'),
        "iat": int(timestamp),
        "exp": int(timestamp + int(config.token().get('lifetime'))),
        "sub": str(identifier),
    }
    secret = config.token().get('secret')
    if not secret:
        secret = config.general().get('secret')
    return jwt.encode(payload, secret, algorithm=config.token().get('algorithm'))


def user_by_token(token, required_scopes=None):
    result = validate(token)
    if result:
        return dict(sub=next((name for name, t in tokens.items() if t == token), None), uid=result)
    return None


def validate(token):
    """
    validate if token is valid and not expired
    :param token: JWT token
    :return: user id, service id, or None if not valid or expired
    """
    if token not in tokens.values():
        logger.warning("invalid token supplied {0}".format(token))
        return None
    name = next((name for name, t in tokens.items() if t == token), None)
    if not name:
        return None
    logger.debug("token request for {0}".format(name))
    try:
        secret = config.token().get('secret')
        if not secret:
            secret = config.general().get('secret')
        jwt.decode(token, secret, algorithms=[config.token().get('algorithm')])
        if 'admin' in session:
            return session['admin']
        if 'service' in session:
            return session['service']
        user = db_session.query(User).filter(User.dom_name == name).one_or_none()
        if not user:
            return None
        return user.id
    except ExpiredSignatureError:
        logger.debug("token {0} for {1} expired, removing it".format(token, name))
        tokens.pop(name, None)
    except JWTError:
        logger.exception("error decoding token")
    return None


def access_secret_verify(access, secret):
    """
    validate access and secret for services
    :param access: access code
    :param secret: sha256 of secret
    :return: service name or None
    """
    try:
        s = db_session.query(Service)
        service = s.filter(Service.access == access).one_or_none()
        if not service:
            logger.warning("could not identify service by id {0}".format(access))
            return None
        if service.secret != hashlib.sha256(secret.encode('utf-8')).hexdigest():
            logger.error("verification failed for service with id {0}".format(access))
        return service.name, service.id
    except Exception as e:
        logger.error("failed login: {0}".format(e))
        return None


def login(username, password):
    """
    login user or service
    :param username: username or service
    :param password: password of sha256(secret)
    :return: token, 200 or 401
    """
    if 'username' in session:
        return "You are already logged in {0}".format(session['username']), 500
    if username == config.admin().get('access') and hashlib.sha256(config.admin().get('secret').encode('utf-8')).hexdigest() == password:
        session['username'] = 'admin'
        session['admin'] = sys.maxsize
        token = generate_token('admin')
        tokens['admin'] = token
        return token, 200
    (service, sid) = access_secret_verify(username, password)
    if service:
        session['username'] = service
        session['service'] = sid
        token = generate_token(service)
        tokens[service] = token
        return token, 200
    if not ldap_manager:
        init_ldap()
    if ldap_manager:
        if AuthenticationResponseStatus.success == ldap_manager.authenticate(username, password):
            session['username'] = username
            token = generate_token(username)
            tokens[username] = token
            return token, 200
    return NoContent, 401


def logout():
    """
    logout user or service
    :return: 200
    """
    if 'username' in session:
        tokens.pop(session['username'], None)
        del(session['username'])
    if 'admin' in session:
        tokens.pop(session['admin'], None)
        del(session['admin'])
    if 'service' in session:
        tokens.pop(session['service'], None)
        del(session['service'])
    if 'token' in session:
        del(session['token'])
    return NoContent, 200
