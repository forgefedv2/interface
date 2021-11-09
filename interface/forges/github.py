# Bridges software forges to create a distributed software development environment
# Copyright © 2021 G V Datta Adithya <dat.adithya@gmail.com>
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

from dateutil.parser import parse as date_parse
import datetime
from urllib.parse import urlparse, urlunparse
import requests

from rfc3339 import rfc3339

from . import utils
from .base import CreateIssue, Forge, RepositoryInfo, CreatePullrequest
from .notifications import Notification, Comment, NotificationResp
from .notifications import ISSUE, REPOSITORY, PULL
from config import settings


class GitHub(Forge):
    def __init__(self):
        """Initializes the class variables"""
        self.host = urlparse(utils.clean_url(settings.from_env("GITHUB").get("HOST")))

    def _get_url(self, path: str) -> str:
        """Retrieves the forge url"""
        if path.startswith("/"):
            path = path[1:]

        url = urlunparse((self.host.scheme, self.host.netloc, path, "", "", ""))
        return url

    def _auth(self):
        """Authorizes the request with a token"""
        return {
            "Authorization": format(
                "token %s" % (settings.from_env("GITHUB").get("API_KEY"))
            )
        }

    def get_forge_url(self) -> str:
        return urlunparse((self.host.scheme, self.host.netloc, "", "", "", ""))

    def get_issues(self, owner: str, repo: str, *args, **kwargs):
        """Get the issues present in a provided repository"""

        # Defining a formatted url with the repo details
        url = self._get_url(format("/repos/%s/%s/issues" % (owner, repo)))
        print(url)

        # Requesting the issues present in the repo
        # GitHub provides a paginated response for 30
        # issues at a time
        response = requests.request("GET", url)

        # returning the responses in the form of JSON
        return response.json()

    def create_issue(self, owner: str, repo: str, issue: CreateIssue):
        """Creates an issue on a repository"""
        url = self._get_url(format("/repos/%s/%s/issues" % (owner, repo)))

        # Defining authorization headers and a payload
        headers = self._auth()
        payload = issue.get_payload()

        # Sending in a POST request
        response = requests.request("POST", url, json=payload, headers=headers)

        # Returns the response with a JSON output
        return response.json()

    def _into_repository(self, data) -> RepositoryInfo:
        """Getting and setting data"""

        info = RepositoryInfo()
        info.set_description(data["description"])
        info.set_name(data["name"])
        info.set_owner_name(data["owner"]["login"])
        return info

    def get_repository(self, owner: str, repo: str) -> RepositoryInfo:
        """Get repository details"""

        url = self._get_url(format("/repos/%s/%s" % (owner, repo)))
        response = requests.request("GET", url)
        data = response.json()
        info = self._into_repository(data)
        print("Payload deets", info.get_payload())
        return info

    def create_repository(self, repo: str, description: str):
        """Creates a repository in the users forge"""
        url = self._get_url("/users/repos/")
        payload = {"name": repo, "description": description}
        headers = self._auth()
        _response = requests.request("POST", url, json=payload, headers=headers)

    def subscribe(self, owner: str, repo: str):
        """Subscribes/watches a repository"""
        url = self._get_url(format("/repos/%s/%s/subscription" % (owner, repo)))
        headers = self._auth()
        _response = requests.request("PUT", url, headers=headers)

    def get_notifications(self, since: datetime.datetime) -> NotificationResp:
        """Notifications for watched repositories"""
        # Setting up a simple query object
        query = {}
        query["since"] = rfc3339(since)
        print("Checking type : ", type(query["since"]))

        # Sending a request for a JSON notifications response
        # to the notifications section
        url = self._get_url("/notifications")
        headers = self._auth()
        response = requests.request("GET", url, params=query, headers=headers)
        notifications = response.json()

        # Setting last_read to a string
        # to be parsed into a datetime
        last_read = query["since"]
        val = []

        for n in notifications:
            # rn: Repository Notification
            rn = Notification()
            subject = n["subject"]
            notification_type = subject["type"]

            # Setting up data for the object
            last_read = n["updated_at"]
            rn.set_updated_at(last_read)
            rn.set_type(notification_type)
            rn.set_title(subject["title"])
            rn.set_state(subject["state"])
            rn.set_repo_url(n["repository"]["html_url"])

            if notification_type == REPOSITORY:
                print(n)
            if notification_type == PULL:
                rn.set_pr_url(
                    requests.request("GET", subject["url"]).json()["html_url"]
                )
                rn.set_upstream(n["repository"]["description"])
                print(n["repository"]["description"])

            if notification_type == ISSUE:
                comment_url = subject["latest_comment_url"]
                print(comment_url)
                if len(comment_url) != 0:
                    resp = requests.request("GET", comment_url)
                    comment = resp.json()
                    if date_parse(comment["updated_at"]) > since:
                        c = Comment()
                        c.set_updated_at(comment["updated_at"])
                        c.set_author(comment["user"]["login"])
                        c.set_body(comment["body"])
                        pr_url = comment["pull_request_url"]
                        if len(comment["pull_request_url"]) == 0:
                            c.set_url(comment["issue_url"])
                        else:
                            url = pr_url
                            c.set_url(comment["pull_request_url"])
                        rn.set_comment(c)
            val.append(rn)
        return NotificationResp(val, date_parse(last_read))

    def create_pull_request(self, owner: str, repo: str, pr: CreatePullrequest):
        """Creates a POST request for the Pull Request"""
        url = self._get_url(format("/repos/%s/%s/pulls" % (owner, repo)))
        headers = self._auth()

        payload = pr.get_payload()
        for key in ["repo", "owner"]:
            del payload[key]

        payload["assignees"] = []
        payload["lables"] = [0]
        payload["milestones"] = 0

        response = requests.request("POST", url, json=payload, headers=headers)
        print(response.json())
        return response.json()


if __name__ == "__main__":
    # Testing the API primitively with a simple call

    # Setting owner and repo
    # owner = "dat-adi"
    # repo = "tmp"
    # g = GitHub()
    # print("HOST : ", g.host)
    # print("GET URL : ", g._get_url(f"/repos/{owner}/{repo}"))
    # print("AUTH : ", g._auth())
    #    print("ISSUES : ", g.get_issues(owner, repo))
    #    print("GET REPO : ", g.get_repository("dat-adi", "tmp"))

    #    issue = CreateIssue()
    #    issue.set_title("another test, to be extra sure.")
    #    print(g.create_issue(owner, repo, issue))
    #    print("SUBSCRIBE : ", g.subscribe("dat-adi", "tmp"))
    # print(
    #     "INTO REPOSITORY : ",
    #     g._into_repository(
    #         {
    #             "name": "G V Datta Adithya",
    #             "description": "Octowhat?",
    #             "owner": {"login": "userwhat?"},
    #         }
    #     ),
    # )

    """
    notifications = g.get_notifications(since=date_parse("2021-10-10T17:06:02+05:30"))
    print(notifications)

    pr = CreatePullrequest()
    pr.set_owner(owner)
    pr.set_repo(repo)
    pr.set_base("main")
    pr.set_head("dev")
    pr.set_title("How many more tests?")
    pr.set_body("Does this create a PR?")
    print(g.create_pull_request(owner, repo, pr))
    """
