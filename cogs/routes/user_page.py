"""
Copyright (c) 2017 Genome Research Ltd.

Authors:
* Simon Beal <sb48@sanger.ac.uk>
* Christopher Harrison <ch12@sanger.ac.uk>

This program is free software: you can redistribute it and/or modify it
under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or (at
your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero
General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

from typing import Dict

from aiohttp.web import Request
from aiohttp_jinja2 import template


@template("user_page.jinja2")
async def user_page(request: Request) -> Dict:
    """
    Set the template context for the user. Show the projects they:
    * Own (including legacy projects);
    * Are involved with;
    * Are in the process of signing up for, front loaded

    :param request:
    :return:
    """
    db = request["db"]
    user = request["user"]
    navbar_data = request["navbar"]

    data = {
        "user":          user,
        "cur_option":    "cogs",
        "first_option":  user.first_option,
        "second_option": user.second_option,
        "third_option":  user.third_option,
        **navbar_data}

    if user.role.review_other_projects:
        data["review_list"] = series_list = db.get_projects_by_cogs_marker(user)

        # TODO Refactor this...or remove it: It looks like it's doing
        # dangerous things!

        # for series in series_list:
        #     for project in series:
        #         set_project_can_mark(request.app, cookies, project)
        #     sort_by_attr(series, "can_mark")

    if user.role.join_projects:
        data["project_list"] = db.get_projects_by_student(user)

    if user.role.create_projects:
        data["series_list"] = series_list = db.get_projects_by_supervisor(user)

        # TODO/FIXME Dragons be here! Remove this if possible

        # for series in series_list:
        #     set_group_attributes(request.app, cookies, series)

    return data
