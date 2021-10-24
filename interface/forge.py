# Bridges software forges to create a distributed software development environment
# Copyright © 2021 Aravinth Manivannan <realaravinth@batsense.net>
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
""" defines basic data structuctures and interfaces used in a forge fed interface"""
import datetime
from urllib.parse import urlparse, urlunparse

from libgit import Repo, InterfaceAdmin, Patch

from .utils import clean_url, get_branch_name, get_patch
from . import local_settings

class Payload:
    """ Payload base class. self.mandatory should be defined"""
    def __init__(self, mandatory: [str]):
        self.payload = {}
        self.mandatory = []

    def get_payload(self):
        """ get payload """
        for f in self.mandatory:
            if self.payload[f] is None:
                raise Exception("%s can't be empty" % f)
        return self.payload

class RepositoryInfo(Payload):
    """ Describes a repository"""
    def __init__(self):
        mandatory = ["name", "owner_name"]
        super().__init__(mandatory)

    def set_name(self, name):
        """ Set name of repository"""
        self.payload["name"] = name

    def set_owner_name(self, name):
        """ Set owner name of repository"""
        self.payload["owner_name"] = name

    def set_description(self, description):
        """ Is this a template repository"""
        self.payload["description"] = description

class CreateIssue(Payload):
    """ Create new issue payload"""
    def __init__(self):
        mandatory = ["title"]
        super().__init__(mandatory)

    def set_title(self,title):
        """ set issue title"""
        self.payload["title"] = title

    def set_body(self,body):
        """ set issue body"""
        self.payload["body"] = body

    def set_due_date(self, due_date):
        """ set issue due date"""
        self.payload["due_date"] = due_date

    def set_closed(self, closed: bool):
        """ set issue open status"""
        self.payload["closed"] = closed

class Comment(Payload):
    def __init__(self):
        mandatory = ["body", "author", "updated_at", "url"]
        super().__init__(mandatory)

    def set_updated_at(self,date):
        """ set comment update time"""
        self.payload["updated_at"] = date

    def set_body(self,body):
        """ set issue body"""
        self.payload["body"] = body

    def set_author(self, author):
        """ set issue author"""
        self.payload["author"] = author

    def set_url(self, url):
        """ set url of comment"""
        self.payload["url"] = url

class Notification(Payload):
    def __init__(self):
        mandatory = ["type", "state", "updated_at", "title"]
        super().__init__(mandatory)

    def set_updated_at(self,date):
        """ set comment update time"""
        self.payload["updated_at"] = date

    def set_type(self,notification_type):
        """ set comment update time"""
        self.payload["type"] = notification_type

    def set_state(self,state):
        """ set comment update time"""
        self.payload["state"] = state

    def set_comment(self,comment: Comment):
        """ set comment update time"""
        self.payload["status"] = comment.get_payload()

    def set_repo_url(self,repo_url: str):
        """ set repository URL update time"""
        self.payload["repo_url"] = repo_url


    def set_title(self,title):
        """ set issue title"""
        self.payload["title"] = title


class NotificationResp:
    def __init__(self, notifications: [Notification], last_read: datetime.datetime):
        self.notifications = notifications
        self.last_read = last_read
    def get_payload(self):
        notifications = []
        for n in self.notifications:
            notifications.append(n.get_payload())

        return notifications

class CreatePullrequest(Payload):
    # see https://docs.github.com/en/rest/reference/pulls
    def __init__(self):
        mandatory = ["owner", "message", "repo", "head", "base", "title"]
        super().__init__(mandatory)

    def set_owner(self, name):
        """ Set owner name of repository"""
        self.payload["owner"] = name

    def set_repo(self, repo):
        """ Set owner name of repository"""
        self.payload["repo"] = repo

    def set_head(self, head):
        """
        From GitHub Docs:

        The name of the branch you want the changes pulled into.
        This should be an existing branch on the current repository.
        You cannot submit a pull request to one repository that requests a merge to
        a base of another repository.
        """
        self.payload["head"] = head

    def set_base(self, base):
        """
        From GitHub Docs:
        The name of the branch you want the changes pulled into.
        This should be an existing branch on the current repository.
        You cannot submit a pull request to one repository that requests a merge to
        a base of another repository.
        """
        self.payload["base"] = base

    def set_title(self, title):
        """ set title of the PR"""
        self.payload["title"] = title

    def set_message(self, message):
        """ set message of the PR"""
        self.payload["message"] = message

    def set_body(self, body):
        """ set title of the PR message"""
        self.payload["body"] = body



class Forge:
    def __init__(self, base_url: str, admin_user: str, admin_email):
        self.base_url = urlparse(clean_url(base_url))
        if all([self.base_url.scheme != "http", self.base_url.scheme != "https"]):
            print(self.base_url.scheme)
            raise Exception("scheme should be wither http or https")
        self.admin = InterfaceAdmin(admin_email, admin_user)

    def get_fetch_remote(self, url: str) -> str:
        """Get fetch remote for possible forge URL"""
        parsed = urlparse(url)
        if all([parsed.scheme != "http", parsed.scheme != "https"]):
            raise Exception("scheme should be wither http or https")
        if parsed.netloc != self.base_url.netloc:
            raise Exception("Unsupported forge")
        repo = parsed.path.split('/')[1:3]
        path = format("/%s/%s" % (repo[0], repo[1]))
        return urlunparse((self.base_url.scheme, self.base_url.netloc, path, "", "", ""))

    def process_patch(self, patch: Patch, local_url: str, upstream_url, branch_name) -> str:
        """ process patch"""
        repo = Repo(local_settings.BASE_DIR, local_url, upstream_url)
        repo.fetch_upstream()
        repo.apply_patch(patch, self.admin, branch_name)

    """ Forge characteristics. All interfaces must implement this class"""
    def get_issues(self, owner: str, repo: str, *args, **kwargs):
        """ Get issues on a repository. Supports pagination via 'page' optional param"""
        raise NotImplementedError

    def create_issue(self, owner: str, repo: str, issue: CreateIssue):
        """ Creates issue on a repository"""
        raise NotImplementedError

    def get_repository(self, owner: str, repo: str) -> RepositoryInfo:
        """ Get repository details"""
        raise NotImplementedError

    def create_repository(self, repo: str, description: str):
        """ Create new repository """
        raise NotImplementedError

    def subscribe(self, owner: str, repo: str):
        """ subscribe to events in repository"""
        raise NotImplementedError

    def get_notifications(self, since: datetime.datetime) -> NotificationResp:
        """ subscribe to events in repository"""
        raise NotImplementedError

    def create_pull_request(self, pr: CreatePullrequest) -> str:
        """
            create pull request
            return value is the URL(HTML page) of the newely created PR
        """
        raise NotImplementedError

    def fork(self, owner: str, repo:str):
        """ Fork a repository """
        raise NotImplementedError

    def close_pr(self, owner: str, repo:str):
        """ Fork a repository """
        raise NotImplementedError
