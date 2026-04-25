import os
import requests
import re
from typing import Optional, List, Dict

class GitHubClient:
    def __init__(self, token: Optional[str] = None, owner: Optional[str] = None):
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.owner = owner or os.getenv("GITHUB_OWNER")
        self.base_url = "https://api.github.com"
        self.graphql_url = "https://api.github.com/graphql"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28"
        } if self.token else {}

    def is_configured(self) -> bool:
        return bool(self.token and self.owner)

    def _graphql_request(self, query: str, variables: Dict = None) -> Dict:
        """Execute GraphQL query/mutation."""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        resp = requests.post(self.graphql_url, headers=self.headers, json=payload, timeout=60)
        resp.raise_for_status()
        result = resp.json()
        if "errors" in result:
            raise Exception(f"GraphQL error: {result['errors']}")
        return result

    def _get_user_node_id(self) -> str:
        """Get the GraphQL node ID for the authenticated user."""
        query = "query { viewer { id login } }"
        result = self._graphql_request(query)
        return result["data"]["viewer"]["id"]

    def _get_repo_node_id(self, repo_name: str) -> str:
        """Get the GraphQL node ID for a repository."""
        query = """
        query GetRepoId($owner: String!, $name: String!) {
            repository(owner: $owner, name: $name) { id }
        }
        """
        result = self._graphql_request(query, {"owner": self.owner, "name": repo_name})
        return result["data"]["repository"]["id"]

    def _get_issue_node_id(self, repo_name: str, issue_number: int) -> str:
        """Get the GraphQL node ID for an issue."""
        query = """
        query GetIssueId($owner: String!, $repo: String!, $num: Int!) {
            repository(owner: $owner, name: $repo) {
                issue(number: $num) { id }
            }
        }
        """
        result = self._graphql_request(query, {"owner": self.owner, "repo": repo_name, "num": issue_number})
        return result["data"]["repository"]["issue"]["id"]

    def create_repo(self, repo_name: str, description: str = "") -> Dict:
        """Create a new repository via REST API."""
        if not self.is_configured(): 
            return {"error": "GitHub not configured"}
        resp = requests.post(
            f"{self.base_url}/user/repos",
            headers=self.headers,
            json={"name": repo_name, "description": description, "private": True, "auto_init": True}
        )
        if resp.status_code in [201, 422]:
            data = resp.json()
            return data if resp.status_code == 201 else {
                "name": repo_name, 
                "html_url": f"https://github.com/{self.owner}/{repo_name}",
                "id": None
            }
        resp.raise_for_status()
        return resp.json()

    def create_project_v2(self, project_name: str, repo_name: str) -> Optional[Dict]:
        """Create a Projects V2 board. Note: V2 projects belong to user/org, not repos."""
        if not self.is_configured(): 
            return None
        try:
            # 1. Get user ID
            user_id = self._get_user_node_id()
            
            # 2. Create the project (V2 projects don't link to repos directly)
            create_query = """
            mutation CreateProject($ownerId: ID!, $title: String!) {
                createProjectV2(input: {ownerId: $ownerId, title: $title}) {
                    projectV2 { id url number }
                }
            }
            """
            result = self._graphql_request(create_query, {"ownerId": user_id, "title": project_name})
            project = result["data"]["createProjectV2"]["projectV2"]
            
            return {
                "id": project["id"],
                "url": project["url"],
                "number": project["number"]
            }
        except Exception as e:
            print(f"⚠️ Projects V2 creation failed: {e}")
            return None

    def create_issue(self, repo_name: str, title: str, body: str, labels: List[str] = None) -> Dict:
        """Create an issue via REST API."""
        if not self.is_configured(): 
            return {"error": "GitHub not configured"}
        payload = {"title": title, "body": body}
        if labels: 
            payload["labels"] = labels
        resp = requests.post(
            f"{self.base_url}/repos/{self.owner}/{repo_name}/issues",
            headers=self.headers,
            json=payload
        )
        resp.raise_for_status()
        return resp.json()

    def add_issue_to_project(self, repo_name: str, issue_number: int, project_id: str) -> bool:
        """Add an existing issue to a Projects V2 board."""
        try:
            issue_id = self._get_issue_node_id(repo_name, issue_number)
            query = """
            mutation AddItemToProject($projectId: ID!, $contentId: ID!) {
                addProjectV2ItemById(input: {projectId: $projectId, contentId: $contentId}) {
                    item { id }
                }
            }
            """
            self._graphql_request(query, {"projectId": project_id, "contentId": issue_id})
            return True
        except Exception as e:
            print(f"⚠️ Failed to add issue to project: {e}")
            return False
