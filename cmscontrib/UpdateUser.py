#!/usr/bin/env python3

# Contest Management System - http://cms-dev.github.io/
# Copyright ? 2016 Stefano Maggiolo <s.maggiolo@gmail.com>
# Copyright ? 2017-2018 Luca Wehrstedt <luca.wehrstedt@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""This script updates an existing user in the database.

"""

# We enable monkey patching to make many libraries gevent-friendly
# (for instance, urllib3, used by requests)
import gevent.monkey
gevent.monkey.patch_all()  # noqa

import argparse
import logging
import sys

from sqlalchemy.exc import IntegrityError

from cms import utf8_decoder
from cms.db import SessionGen, User
from cmscommon.crypto import generate_random_password, build_password, \
    hash_password


logger = logging.getLogger(__name__)


def edit_user(first_name, last_name, username, password, method, is_hashed,
             email, timezone, preferred_languages):
    
    if password is None:
        assert not is_hashed
    else:
        if is_hashed:
            stored_password = build_password(password, method)
        else:
            stored_password = hash_password(password, method)

    if preferred_languages is not None:
        preferred_languages = list(
            lang.strip() for lang in preferred_languages.split(",") if
            lang.strip())

    logger.info("Finding the user in the database.")
    updated = True
    updated_fields = []
    try:
        with SessionGen() as session:
            user = session.query(User)\
                .filter(User.username == username).first()
            if user is None:
                logger.error("User %s does not exist.", username)
                return False

            if password is not None and user.password != stored_password:
                user.password = stored_password
                updated_fields.append("Password")

            if preferred_languages is not None and user.preferred_languages != user.preferred_languages:
                user.preferred_languages = preferred_languages
                updated_fields.append("Preferred Languages")
            
            if user.first_name != first_name:
                user.first_name = first_name
                updated_fields.append("First Name")

            if user.last_name != last_name:
                user.last_name = last_name
                updated_fields.append("Last Name")
            
            if user.email != email:
                user.email = email
                updated_fields.append("Email")

            if user.timezone != timezone:
                user.timezone = timezone
                updated_fields.append("Timezone")
            
            session.commit()
    except IntegrityError:
        logger.error("Unable to edit user - IntegrityError")
        return False

    if len(updated_fields) == 0:
        logger.error("User %s was not edited" % username)
        return False
    
    logger.info("User %s updated, changed: %s" % 
                (username, ", ".join(updated_fields)))
    return True


def main():
    """Parse arguments and launch process.

    """
    parser = argparse.ArgumentParser(description="Add a user to CMS.")
    parser.add_argument("first_name", action="store", type=utf8_decoder,
                        help="given name of the user")
    parser.add_argument("last_name", action="store", type=utf8_decoder,
                        help="family name of the user")
    parser.add_argument("username", action="store", type=utf8_decoder,
                        help="username used to log in")
    parser.add_argument("-e", "--email", action="store", type=utf8_decoder,
                        help="email of the user")
    parser.add_argument("-t", "--timezone", action="store", type=utf8_decoder,
                        help="timezone of the user, e.g. Europe/London")
    parser.add_argument("-l", "--languages", action="store", type=utf8_decoder,
                        help="comma-separated list of preferred languages")
    password_group = parser.add_mutually_exclusive_group()
    password_group.add_argument(
        "-p", "--plaintext-password", action="store", type=utf8_decoder,
        help="password of the user in plain text")
    password_group.add_argument(
        "-H", "--hashed-password", action="store", type=utf8_decoder,
        help="password of the user, already hashed using the given algorithm "
             "(currently only --bcrypt)")
    method_group = parser.add_mutually_exclusive_group()
    method_group.add_argument(
        "--bcrypt", dest="method", action="store_const", const="bcrypt",
        help="whether the password will be stored in bcrypt-hashed format "
             "(if omitted it will be stored in plain text)")

    args = parser.parse_args()

    if args.hashed_password is not None and args.method is None:
        parser.error("hashed password given but no method specified")

    success = edit_user(args.first_name, args.last_name, args.username,
                       args.plaintext_password or args.hashed_password,
                       args.method or "plaintext",
                       args.hashed_password is not None, args.email,
                       args.timezone, args.languages)
    return 0 if success is True else 1


if __name__ == "__main__":
    sys.exit(main())