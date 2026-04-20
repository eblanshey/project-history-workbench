# PLAN toward MVP

The goal of this document is to define the high-level implementation phases/steps which implement the final @docs/ProjectState.md. 

## Already Done

- Snapshots per-document
- Exporting/importing snapshots via YAML
- Calculating node and property diffs based on two snapshots
- UI to view node and property diffs

## Implementation Phases

### Phase 1 - git repository detection

Detect the active Git repository based on open FreeCAD documents and display its name and path in the UI.
Action: FindActiveGitRepository

- Create a models.py file in a new `domain/git` directory. Define the "GitRepository" model there.
- Create an ApplicationState.py file within the `ui/presenters` directory, with an ApplicationState which is an in-memory state class. Define the "git_repository: GitRepository" property. It can be used within the UI layer only.
- The Container creates a new ApplicationState singleton instance which can be used only within the ui/presentation layer (add comments for this)
- Create GitPort protocol in `domain/git/ports.py` with `find_top_level_path() -> Path|None` method.
- Create GitService in `domain/git/git_service.py` with `get_repository(path) -> GitRepository|None` method
  - Calls the GitPort for the given path and if Path found, create and return new GitRepository instance
- Implement the adapter in the infrastructure layer, in `infrastructure/git` dir.
  - It should return GitRepository instance given a file path, otherwise return None if not exists.
- In `application/actions/result_models.py` add generic Result which will be returned by ALL actions we create from now on.
  - is_success: bool
  - data: Optional[Any] = None  (on success) 
  - message: Optional[str] = None  (on error)
- Create action FindActiveGitRepository which grabs list of all open freecad document paths, and one by one tries to get the git repository using GitService. Returns the first repository it encounters.
  - Presenter layer is updated to make the call to FindActiveGitRepository when initializing the UI when workbench is first activated. Sets the returned GitRepository to the application state.
- The UI is updated to display the current git repository in format: [name] ([path]). Example: `my_project (/home/user/documents)`, where my_project corresponds to the git directory name
  - Displayed above the current list of snapshots in the UI

Question: is the ApplicationState a good solution and fits well with the rest of the design?

### Phase 2 - loading git commits

Fetch and display the last 20 Git commits in a new UI list.
Action: GetCommits

- in `domain/git/models.py` add GitCommit, with properties id (the hash), message, author, and timestamp.
- Update git port/adapter to return a dictionary of last 20 commits given git path
- In GitService add method "get_commits(GitRepository)" which returns only the last 20 GitCommits (for the MVP), uses the adapter. Returns in DESC order.
- Create action GetCommits(GitRepository), which calls the GitService
- Update the presenter to call the action, then pass commits to the view for display
- Create a new sub-view which displays all the commits in a QListWidget. This will replace the existing Snapshot list widget. Let's call this the History widget. 
  - Make the Commit QListWidget display the first 7 chars of the commit, author, and timestamp on one line, and the first line of the message on the second line (and wrap to next line if first line too long). Tooltip or popover can display the full message.
  - Do not select a commit automatically on load -- nothing should be selected
- The GitRepositoryPresenter can be used to "own" this part of the view that deals with commit list.
- Update the _detect_git_repository method to automatically trigger loading the commits. This means that the "on_refresh_clicked" will also trigger reloading commits.
- The "History" label can be placed below the existing repository name label (the QHBoxLayout), and "Snapshots" label removed.
- Add a "Reload" button next to the repository name to refresh current git repository and commit list

Questions:
- Is QListWidget the best widget type to use for commits? 

### Phase 3 - add Working Tree and Staging items

- In presentation/view, manually add "Working Tree" and "Staging" items to the top of the Commit list, centering the text there. No other text needed on that item.
- These items MUST always be present when loading the commit list, so it should be part of the commit loading logic.
- Order: Working Tree, Staging, then the commits

### Phase 4 - Domain prep for snapshots

Update domain models and logic to support Git paths and snapshot-based comparisons.

- Update Snapshot entity to have a "git_path" string variable, which is the relative path from the git root
- Update DiffResult entity to have "old_snapshot: Snapshot" and "new_snapshot: Snapshot"
  - Remove old_snapshot_name and "new_snapshot_name"
- Update DiffResult entity to have a "warnings" list property:
  - The list can contain a list of strings with warning
- Update TreeComparator.compare_snapshots to:
  - accept Snapshot instances instead of nodes (old_snapshot and new_snapshot) (update usages)
  - Create DiffResult with the snapshots
- Update DiffResult constructor: of the instance of old and new snapshots are the same instance, set the warning in the warning list
- Update DiffEngine.compare to accept None for old_snapshot:
  - If None, then pass the new snapshot to old snapshot as well (same snapshot)
- Update SnapshotExtractor.extract_tree() to take a DocumentLike required argument instead of port.
  - This should be a sub-phase of its own, as it creates changes to downstream dependency.
- Update the view tree widget that displays the tree nodes to have the top-level item be the DiffResult.new_snapshot.git_path. Then the nodes under it is the same tree view.
  - With this done, the tree view supports multiple document diffs.

### Phase 5 - Start of working tree diff implementation

- In DiffResult, add static property WARNING_OLD_SNAPSHOT_MISSING = WARNING_OLD_SNAPSHOT_MISSING
- In GitService add method `get_eligible_docs(GitRepository, list[DocumentLike])`:
    - First arg: the active GitRepository
    - Second arg: list of DocumentLike (can be taken from all open freecad documents)
    - Returns: list of DocumentLike that is within the GitRepository directory (files do not need to be tracked, just in the git dir)
- Create action GetOpenEligibleDocuments:
  - Uses freecad port to get all open documents
  - Pass them to GitService.get_eligible_docs()
  - Returns list of DocumentLike
- Create action CreateDocumentSnapshotForWorkingTree(GitRepository, document: DocumentLike):
  - Validation: document must be in the git repository, otherwise return error
  - Generate a Snapshot for the given document using SnapshotExtractor.extract_tree()
  - Return snapshot
- Create stub action CreateDocumentSnapshotForCommit(GitRepository, commit: string, git_path: string):
  - Set return type to Snapshot|None.
  - For now just return None
- Create action CreateDiff(old_snapshot: Snapshot|None, new_snapshot: Snapshot):
  - return result of DiffEngine.compute_diff, which returns DiffResult
  - If None is passed for old snapshot, then run 
- Presentation logic: add listener for when an item is selected in the History widget.
  - Wire up the logic for when the Working Tree item is selected:
    - GetOpenEligibleDocuments
    - CreateDocumentSnapshotForWorkingTree
    - CreateDocumentSnapshotForCommit
    - CreateDiff - if the commit snapshot doesn't exist, pass the same Snapshot for both arguments.
  - It should populate the existing diff widget with the resulting diff. Put these actions into a presentation-level orchestration method (what should we call it and where does it live?) so that it can be reused.
  - In the view, if the DiffResult.warnings contains WARNING_OLD_SNAPSHOT_MISSING, add a warning sign emoji (U+26A0) with a tooltip over it with text: "Old snapshot missing"

Questions: where should we store the DiffResults for application state? Should we store them in the ApplicationState? Is that the right place? Is the DiffResult something that belongs in presentation layer or view layer? In the next phase we'll need to be able to add Snapshots to git staging, which entails extracting them from the DiffResult.

### Phase 6 - Adding Files to Staging

- In the Working Tree node tree in the view, update it so that each top-level document item has a "+ Add" button aligned to the right
    - Documents that don't have any changes (based on the DiffResult state) should have the "+" button disabled
- In GitService, add method `stage_files(GitRepository, git_paths: list[str])` which takes a list of string paths relative to git root
    - Create the corresponding GitPort/Adapter to add the files, and use it
- Create new action StageDocuments(GitRepository, list[Snapshot]):
    - Create an empty list to store all relative paths to add to git
    - For each snapshot:
        - Use SnapshotYamlSerializer to persist snapshot to disk
            - The path should be in a `.snapshots` directory in the same directory as the file.
            - Ex: if git_path is `path/to/mydoc.FCStd`, snapshot is persisted to `path/to/.snapshots/mydoc.yaml
            - If the file already exists it should be overwritten.
        - Add the FCStd and the yaml file to the list to add
    - Use GitService to add all paths to git staging
- Update presentation/view:
  - When the Add button is pressed, it calls the StageDocuments action we just created, with the Snapshot associated with the "new" snapshots in the DiffResult associated with that document.
  - Then it calculates the diff again using CreateDocumentSnapshotForWorkingTree -> CreateDocumentSnapshotForCommit -> CreateDiff. If everything is working correctly, the diff result will show no changes.

Question: where do we put the logic that determines the correct snapshot directory for a file? We'll need to use it in the following phases, too.

### Phase 7 - Staging Diff

- In GitService, add get_staged_files(GitRepository): returns list of freecad staged files
  - For each FCStd file staged, return the git_path string (return list)
- In GitService, add `get_file_contents(GitRepository, commit: string|None, git_path: str)`
  - Runs `git show` for the requested file and commit. If commit is None, use the index.
  - Make sure that "commit" accepts common acceptable git formats, like hash or "HEAD" or "HEAD~2".
  - Returns the file contents as a string.
- Refactor SnapshotYamlSerializer:
  - Create new public static method `from_yaml_file`: should do what the current `from_yaml` method does
  - Change `from_yaml` to take a yaml string as an argument
  - `from_yaml_file` uses `from_yaml` to return the snapshot
- Create action GetStagedFilePaths(GitRepository): just calls and returns result of get_staged_files
- Add meat to our action CreateDocumentSnapshotForCommit:
  - When "commit" arg is None (the "index" option)
    - Determine the location of the snapshot for the FCStd git path provided (use the function we created in phase 6)
    - Grab the snapshot yaml file contents from the index using GitService.get_file_contents
    - Use the SnapshotYamlSerializer.from_yaml to create the snapshot and return it
  - When "commit" arg is not None:
    - Same logic as above, but gets file contents from the given commit hash or name
  - In both cases if the file does not exist, return None
- Update our presentation listener so that when the Staging History item is selected, it triggers this logic:
  - GetStagedFilePaths
  - For each path:
    - CreateDocumentSnapshotForCommit (for index)
    - CreateDocumentSnapshotForCommit (for HEAD)
    - CreateDiff
  - Return list of DiffResults
- Set the view to displays those diffs.
- For paths where CreateDocumentSnapshotForCommit for index returns None, in the tree diff widget create a one-level, flat item for that diff with a "Warning" icon, similar to how we do elsewhere, with tooltip "Snapshot missing." It will not have the tree below it.

### Phase 8 - Commits

- In GitPort and Adapter, add method "commit(git_root: str, message: str) which just runs the git commit command.
- In GitService, add commit(GitRepository, message) and implement it
- Add a new Action, CommitStaging(GitRepository, str: message), which just calls the git service. Return success: true on success.
- Create a new Command that should be visible from the toolbar, called Commit.
  - When pressed, a new popup should open with a text box to enter the commit message. 
  - When "Commit" is pressed, it runs the CommitStaging action. The GitRepository should be taken from the UIState.
    - If UIState doesn't have a GitRepository, then the warning should open and say "No git repository detected." instead of the message popup.
  - If "Cancel" is pressed, the popup closes.
  - When the action succeeds, the presentation layer should be updated to reload the commits (there's a method for it already.)

### Phase 9 - Diffs for Commits

- In GitPort/Adapter, implement get_committed_files(git_root: str, commit: str) which returns all changed FCStd files for the given commit (hash or HEAD, or HEAD^, etc)
- Add get_committed_files(GitRepository, commit: str) to GitService
- Create new Action GetCommittedFilePaths which calls the git service
- Update our presentation listener so that when a Commit item is selected, it triggers this logic:
  - GetCommittedFilePaths is called for the given commit to get a full list of changes paths
  - GetCommittedFilePaths is called for the parent of the given commit
  - For each path:
    - CreateDocumentSnapshotForCommit (for COMMIT)
    - CreateDocumentSnapshotForCommit (for COMMIT^)
    - CreateDiff
  - Return list of DiffResults
- Set the view to displays those diffs.
