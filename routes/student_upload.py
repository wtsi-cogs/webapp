import glob
import os
from datetime import datetime, timedelta

import aiofiles
from aiohttp import web
from aiohttp_jinja2 import template

import scheduling.grace_deadline
from db_helper import get_user_cookies, get_most_recent_group, get_project_id
from permissions import view_only, get_permission_from_cookie


@template('student_upload.jinja2')
@view_only("join_projects")
async def student_upload(request):
    session = request.app["session"]
    cookies = request.cookies
    group = get_most_recent_group(session)
    project = [project for project in group.projects if project.student_id == get_user_cookies(cookies)][0]
    if project.grace_passed:
        return web.Response(status=403, text="Grace time exceeded")
    scheduler = request.app["scheduler"]
    job = scheduler.get_job(f"grace_deadline_{project.id}")
    project_grace = None
    if job:
        project_grace = job.next_run_time.strftime('%Y-%m-%d %H:%M')
    return {"project": project,
            "grace_time": request.app["misc_config"]["submission_grace_time"],
            "project_grace": project_grace}


@view_only("join_projects")
async def on_submit(request):
    session = request.app["session"]
    group = get_most_recent_group(session)
    cookies = request.cookies
    user_id = get_user_cookies(cookies)
    project = [project for project in group.projects if project.student_id == user_id][0]
    if not project.uploaded:
        #FIXME Change seconds to days
        scheduling.grace_deadline.add_grace_deadline(request.app["scheduler"],
                                                     project.id,
                                                     datetime.now() + timedelta(seconds=request.app["misc_config"]["submission_grace_time"]))
        project.uploaded = True
        project.grace_passed = False
    elif project.grace_passed:
        return web.json_response({"error": "Grace time exceeded"})
    reader = await request.multipart()
    await reader.next()
    # aiohttp does weird stuff and doesn't set content headers correctly so we've got to do it manually
    uploader = await reader.next()
    filename = await uploader.read()
    extension = filename.rsplit(b".", 1)[1][:4].decode("ascii")
    user_path = os.path.join("upload", str(user_id))
    if not os.path.exists(user_path):
        os.mkdir(user_path)
    filename = os.path.join(user_path, f"{group.series}_{group.part}.")
    existing_files = glob.glob(filename+"*")
    if existing_files:
        for path in existing_files:
            os.remove(path)
    # Again, now to read the actual file
    await reader.next()
    uploader = await reader.next()
    async with aiofiles.open(filename+extension, mode="wb") as f:
        while True:
            chunk = await uploader.read_chunk()  # 8192 bytes by default.
            if not chunk:
                break
            await f.write(chunk)
    return web.json_response({"success": True})


async def download_file(request):
    session = request.app["session"]
    cookies = request.cookies
    project_id = int(request.match_info["project_id"])
    project = get_project_id(session, project_id)
    user_id = get_user_cookies(cookies)
    if user_id in (project.student_id, project.cogs_marker_id, project.supervisor_id) or \
            get_permission_from_cookie(request.app, cookies, "view_all_submitted_projects"):
        filename = get_stored_path(project)
        if filename:
            return web.FileResponse(filename,
                                    headers={"Content-Disposition": f'inline; filename="{project.student.name}_{os.path.basename(filename)}"'})
        return web.Response(status=404, text="Not found")
    return web.Response(status=403, text="Not authorised")


def get_stored_path(project):
    user_path = os.path.join("upload", str(project.student_id))
    if os.path.exists(user_path):
        filename = os.path.join(user_path, f"{project.group.series}_{project.group.part}.*")
        existing_files = glob.glob(filename)
        assert len(existing_files) <= 1
        if existing_files:
            return existing_files[0]
