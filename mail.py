import smtplib
from asyncio import get_event_loop
from concurrent.futures import ThreadPoolExecutor
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict

from bs4 import BeautifulSoup, NavigableString, CData
from jinja2 import Environment, BaseLoader


async def send_user_email(app, user, template_name, attachments=None, **kwargs):
    config = app["email"]
    web_config = app["webserver"]

    template = app["email_templates"][template_name]
    subject = Environment(loader=BaseLoader).from_string(template["subject"])
    contents = Environment(loader=BaseLoader).from_string(template["contents"])

    await send_email(to=user.email,
                     subject=subject.render(config=config, user=user, web_config=web_config, **kwargs),
                     contents=contents.render(config=config, user=user, web_config=web_config, **kwargs),
                     attachments=attachments,
                     **config)


async def send_email(*, host, port, to, from_, subject, contents, attachments: Dict[str, bytes]=None):
    loop = get_event_loop()
    with ThreadPoolExecutor() as executor:
        loop.run_in_executor(executor, _send_email, host, port, to, from_, subject, contents, attachments)


def _send_email(host, port, to, from_, subject, contents, attachments: Dict[str, bytes]=None):
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = from_
    message["To"] = to

    html = contents
    soup = BeautifulSoup(html, "html.parser")
    text = get_text(soup)
    message.attach(MIMEText(text, 'plain'))
    message.attach(MIMEText(html, 'html'))

    if attachments is not None:
        for name, data in attachments.items():
            part = MIMEApplication(
                data,
                Name=name
            )
            part["Content-Disposition"] = f'attachment; filename="{name}"'
            message.attach(part)

    s = smtplib.SMTP(host, port)
    s.set_debuglevel(1000)
    s.sendmail(from_, to, message.as_string())
    s.quit()


def get_text(soup):
    rtn = []
    for descendant in soup.descendants:
        if isinstance(descendant, (NavigableString, CData)):
            parent = descendant.parent
            if parent.name == "a":
                rtn.append(f"{descendant} ({parent['href']})")
            else:
                rtn.append(str(descendant))
    return "".join(rtn)


if __name__ == "__main__":
    import os
    from config import load_config
    config = load_config(os.path.join("config", "config.yaml"))["email"]
    config["from_"] = config["from"]
    del config["from"]
    _send_email(to="sb48@sanger.ac.uk",
                subject="test",
                contents="<h1>test</h1> <a href='http://127.0.0.1/project_feedback/2'>mark their project</a>",
                attachments={"filename.txt": b"test"},
                **config)