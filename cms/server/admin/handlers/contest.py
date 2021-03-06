#!/usr/bin/env python2
# -*- coding: utf-8 -*-

# Contest Management System - http://cms-dev.github.io/
# Copyright © 2010-2013 Giovanni Mascellani <mascellani@poisson.phc.unipi.it>
# Copyright © 2010-2015 Stefano Maggiolo <s.maggiolo@gmail.com>
# Copyright © 2010-2012 Matteo Boscariol <boscarim@hotmail.com>
# Copyright © 2012-2015 Luca Wehrstedt <luca.wehrstedt@gmail.com>
# Copyright © 2014 Artem Iglikov <artem.iglikov@gmail.com>
# Copyright © 2014 Fabian Gundlach <320pointsguy@gmail.com>
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

"""Contest-related handlers for AWS.

"""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from cms import ServiceCoord, get_service_shards, get_service_address
from cms.db import Contest
from cmscommon.datetime import make_datetime

from .base import BaseHandler, SimpleContestHandler, SimpleHandler


class AddContestHandler(SimpleHandler("add_contest.html")):
    """Adds a new contest.

    """
    def post(self):
        fallback_page = "/contests/add"

        try:
            attrs = dict()

            self.get_string(attrs, "name", empty=None)
            self.get_string(attrs, "description")

            assert attrs.get("name") is not None, "No contest name specified."

            allowed_localizations = \
                self.get_argument("allowed_localizations", "")
            if allowed_localizations:
                attrs["allowed_localizations"] = \
                    [x.strip() for x in allowed_localizations.split(",")
                     if len(x) > 0 and not x.isspace()]
            else:
                attrs["allowed_localizations"] = []

            attrs["languages"] = self.get_arguments("languages")

            self.get_bool(attrs, "submissions_download_allowed")
            self.get_bool(attrs, "block_hidden_participations")
            self.get_bool(attrs, "ip_restriction")
            self.get_bool(attrs, "ip_autologin")

            self.get_string(attrs, "token_mode")
            self.get_int(attrs, "token_max_number")
            self.get_timedelta_sec(attrs, "token_min_interval")
            self.get_int(attrs, "token_gen_initial")
            self.get_int(attrs, "token_gen_number")
            self.get_timedelta_min(attrs, "token_gen_interval")
            self.get_int(attrs, "token_gen_max")

            self.get_int(attrs, "max_submission_number")
            self.get_int(attrs, "max_user_test_number")
            self.get_timedelta_sec(attrs, "min_submission_interval")
            self.get_timedelta_sec(attrs, "min_user_test_interval")

            self.get_datetime(attrs, "start")
            self.get_datetime(attrs, "stop")

            self.get_string(attrs, "timezone", empty=None)
            self.get_timedelta_sec(attrs, "per_user_time")
            self.get_int(attrs, "score_precision")

            # Create the contest.
            contest = Contest(**attrs)
            self.sql_session.add(contest)

        except Exception as error:
            self.application.service.add_notification(
                make_datetime(), "Invalid field(s)", repr(error))
            self.redirect(fallback_page)
            return

        if self.try_commit():
            # Create the contest on RWS.
            self.application.service.proxy_service.reinitialize()
            self.redirect("/contest/%s" % contest.id)
        else:
            self.redirect(fallback_page)


class ContestHandler(SimpleContestHandler("contest.html")):
    def post(self, contest_id):
        contest = self.safe_get_item(Contest, contest_id)

        try:
            attrs = contest.get_attrs()

            self.get_string(attrs, "name", empty=None)
            self.get_string(attrs, "description")

            assert attrs.get("name") is not None, "No contest name specified."

            allowed_localizations = \
                self.get_argument("allowed_localizations", "")
            if allowed_localizations:
                attrs["allowed_localizations"] = \
                    [x.strip() for x in allowed_localizations.split(",")
                     if len(x) > 0 and not x.isspace()]
            else:
                attrs["allowed_localizations"] = []

            attrs["languages"] = self.get_arguments("languages")

            self.get_bool(attrs, "submissions_download_allowed")
            self.get_bool(attrs, "block_hidden_participations")
            self.get_bool(attrs, "ip_restriction")
            self.get_bool(attrs, "ip_autologin")

            self.get_string(attrs, "token_mode")
            self.get_int(attrs, "token_max_number")
            self.get_timedelta_sec(attrs, "token_min_interval")
            self.get_int(attrs, "token_gen_initial")
            self.get_int(attrs, "token_gen_number")
            self.get_timedelta_min(attrs, "token_gen_interval")
            self.get_int(attrs, "token_gen_max")

            self.get_int(attrs, "max_submission_number")
            self.get_int(attrs, "max_user_test_number")
            self.get_timedelta_sec(attrs, "min_submission_interval")
            self.get_timedelta_sec(attrs, "min_user_test_interval")

            self.get_datetime(attrs, "start")
            self.get_datetime(attrs, "stop")

            self.get_string(attrs, "timezone", empty=None)
            self.get_timedelta_sec(attrs, "per_user_time")
            self.get_int(attrs, "score_precision")

            # Update the contest.
            contest.set_attrs(attrs)

        except Exception as error:
            self.application.service.add_notification(
                make_datetime(), "Invalid field(s).", repr(error))
            self.redirect("/contest/%s" % contest_id)
            return

        if self.try_commit():
            # Update the contest on RWS.
            self.application.service.proxy_service.reinitialize()
        self.redirect("/contest/%s" % contest_id)


class OverviewHandler(BaseHandler):
    """Home page handler, with queue and workers statuses.

    """

    def get(self, contest_id=None):
        if contest_id is not None:
            self.contest = self.safe_get_item(Contest, contest_id)

        self.r_params = self.render_params()
        self.render("overview.html", **self.r_params)


class ResourcesListHandler(BaseHandler):
    def get(self, contest_id=None):
        if contest_id is not None:
            self.contest = self.safe_get_item(Contest, contest_id)

        self.r_params = self.render_params()
        self.r_params["resource_addresses"] = {}
        services = get_service_shards("ResourceService")
        for i in range(services):
            self.r_params["resource_addresses"][i] = get_service_address(
                ServiceCoord("ResourceService", i)).ip
        self.render("resourceslist.html", **self.r_params)
