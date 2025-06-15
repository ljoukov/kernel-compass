from pathlib import Path
import kit
from kit.summaries import OpenAIConfig, AnthropicConfig, GoogleConfig
from dotenv import load_dotenv
import os
from git import Repo as GitRepo
from datetime import datetime, timedelta
from kit import Repository, Summarizer
import pandas as pd, rich
from tqdm import tqdm


current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
REPO_PATH=str(Path(current_dir / '../linux-90d/').resolve())


print(REPO_PATH)
load_dotenv(dotenv_path=current_dir / '../.env')

kit_repo = kit.Repository(path_or_url=REPO_PATH)

openai_custom_config = OpenAIConfig(
  api_key=os.environ.get("OPENAI_API_KEY"),
  model="gpt-4o-mini"
)

summarizer = kit_repo.get_summarizer(config=openai_custom_config)
# openai_summary = openai_summarizer.summarize_file("fs/aio.c")
# print(f"OpenAI Summary:\n{openai_summary}")


repo_git = GitRepo(REPO_PATH)
since = datetime.now() - timedelta(days=90)
commits = [c for c in repo_git.iter_commits('master') if datetime.fromtimestamp(c.committed_date) >= since]

def classify_vendor(email):
    domain = email.split("@")[-1]
    mapping = {"intel.com":"Intel", "amd.com":"AMD", "google.com":"Google"}
    return mapping.get(domain, "Other")

records = []
for c in tqdm(commits):
    diff = c.diff(c.parents[0] if c.parents else None, create_patch=True)
    vendor = classify_vendor(c.author.email)
    for d in diff.iter_change_type('M'):   # M,A,D etc.
        path = d.b_path
        # Cheap subsystem bucket
        if path.startswith("drivers/"):
            subsystem = path.split("/")[1]
        else:
            subsystem = path.split("/")[0]
        # Optional symbol extraction on touched file
        symbols = [s["name"] for s in kit_repo.extract_symbols(path)]
        records.append({
            "sha": c.hexsha,
            "vendor": vendor,
            "subsystem": subsystem,
            "file": path,
            "symbols": symbols,
            "insertions": d.diff.decode().count('\n+') ,
            "deletions": d.diff.decode().count('\n-')
        })

df = pd.DataFrame(records)
table = df.groupby(["vendor","subsystem"]).size().unstack(fill_value=0)
rich.print(table)
print(table.columns)
table.to_csv(current_dir / "vendor_subsystem_table.csv")