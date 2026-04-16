# PROJECT STATE for MVP

The goal of this workbench is to help FreeCAD users track and verify parametric changes in their CAD models by comparing document snapshots, ensuring that modifications (like changing a dimension from 2mm to 3mm) don't cause unintended downstream effects on other features or properties. This document outlines the overall plan to get to MVP.

## Current application state

- In-memory snapshots of the active freecad document
- Ability to compare two arbitrarily selected freecad documents
- Displays diff of freecad feature tree with highlighted nodes
- Clicking a node displays the node's properties, comparing values before and after

## Functionality to Add

- Git integration
- Diffing more than one active document at a time
- Persisting snapshots in YAML files, with a standardized way of mapping YAML snapshots to their respective freecad documents
- Automatically select the git project by going through all open document file locations until one is found to be in a git repository
    - "Refresh" button to reload git repository and commits
- Empty state message when no eligible documents are open
- The commit list should contain:
    - One entry for every commit in the active git repository, sorted in DESC date order
    - One entry for "Working Tree", above the commit entries. This compares working files to the "index", which is staging or HEAD
    - One entry for "Staging", below "Working Tree". This compares staged files to HEAD.
- Selecting a commit in the list should automatically display the diff between it and the previous commit, using the standard object node diff + property diff viewer
- Diffing does NOT actually use "git diff", but compares two snapshots using our functionality
- Ability to git commit freecad documents

## How Working Tree and Staging Trees are loaded

Note: for working tree and staging tree, the only docs eligible for viewing and diffing are the ones available in both the active git repository directory AND open in freecad, so (REPOSITORY_DOCS & OPEN_IN_FREECAD). Diffing commits between each other doesn't have this limitation. We'll refer to the unioned files as "Eligible Docs".

High-level flow for generating the diff:

1. `git diff` is internally used to see which documents have changes in the active repository -- the exact git changes don't matter
2. For each eligible doc, create a snapshot in-memory (existing functionality). We can call it the "dirty" snapshot.
3. `git diff --cached` is internally used to see which docs are staged -- exact git changes don't matter
4. The snapshots for the corresponding eligible files are loaded
5. Populate the Working Tree with diffs comparing the dirty snapshots to the staging snapshots
    1. If a dirty snapshot doesn't have a corresponding staging snapshot, the one from the last commit is used (similar to `git diff` command)
6. Populate the Staging Tree with diffs comparing staged eligible documents with the corresponding HEAD snapshots

## Commit Flow

- Each document in the Working Tree has an "+" button to the right which can be clicked.
- Clicking "+" on a document does the following:
    - Persist the snapshot to a YAML file
    - Run `git add [doc_path] [yaml_path]`
- The trees are updated respectively -- the doc is removed from Working tree and shows up in Staging
- User presses the "Commit" button in the toolbar, which opens a QInputDialog where they type a message and presses commit: the staged files are committed
- The staging tree is cleared and a new commit is added to the commit list

## YAML Snapshots

- Snapshots are stored in YAML files, to be able to diff using text-based tools in addition to this workbench
- Snapshots are stored in a `.snapshots` directory at in the same directory as the freecad file
- Snapshots have the same name as the freecad document

Examples freecad directory:

___
- .snapshots/File1.yaml
- File1.FCStd
- mydir/.snapshots/File2.yaml
- mydir/File2.FCStd
___

If File1.FCStd is staged, for example, the Staging tree will compare, using our snapshot comparison functionality, the staged `.snapshots/File1.yaml` file to the same yaml file as it exists in HEAD commit.

### Snapshot File Structure

```yaml
---
v: snapshot_version
timestamp: [in UTC]
uid: 2b50a4d3-05d2-48e9-a1bf-2dce33ce69e0  # doc id
objects:
- id: 43
  type_id: Sketcher::SketchObject
  name: Sketch
  after: 
  properties:
      - Contraints:
            - FirstValue
            - SecondValue
      - Label: MySketch
  path: Pad/Sketch
- id: 47
  type_id: PartDesign::Pad
  name: Pad
  after: Sketch002
  properties:
      - Length: 43mm
      - Label: MyPad
  path: Pad
- id: 48
  type_id: Sketcher::SketchObject
  name: Sketch002
  ...
```

Key points:
- objects are stored in order of the integer id -- this never changes
- the "after" is used for ordering objects on the same hierarchical level
- circular references (A -> parent B -> A) are not allowed

## Git commands supported

- git add [file]
- git commit -m "[message]"

## Application-level Actions needed

All actions return a Result object with properties:
- is_success: bool
- data: Optional[Any] = None  (on success)
- message: Optional[str] = None  (on error)

Actions to add:
- FindActiveGitRepository: looks up the git repository root path from open freecad documents. Return: Result with GitRepository in data.
- GetCommits(GitRepository): fetches commits and their messages from the given repository. Return: Result with list[GitCommit] in data.
- GetOpenEligibleDocuments(GitRepository): returns a list of documents in the active repository (eligible docs)
- GetStagedFilePaths(GitRepository): returns a list of staged git_paths in the active repository
- GetCommittedFilePaths(GitRepository, commit: string): returns a list of freecad git_paths in the active repository for the given commit
- CreateDocumentSnapshotForCommit(GitRepository, commit: string, git_path: string): returns a Snapshot object for the given file at commit. Passing "None" for the commit gets it from the index (similar to `git show :file`), so from staging or HEAD
- CreateDocumentSnapshotForWorkingTree(GitRepository, document: DocumentLike): returns a Snapshot object for the given file in the working tree. 
- CreateDiff(Snapshot, Snapshot): Computes diff for the given snapshots
- StageDocuments(GitRepository, list[str]: docs): stages the given list of documents. Generates a snapshot for each one, persists to YAML, and `git add [doc_path] [yaml_path]` for each one. Return: Result with bool success in data.
- CommitStaging(GitRepository, str: message): simply does a `git commit -m "[message]"`. Does not add files or generate snapshots. Return: Result with bool success in data.

## User Flows with Action Usage

1. Workbench startup
   1. FindActiveGitRepository: Detect git repository from opened documents
   2. GetCommits: Load last 20 commits into the sidebar with their git messages, and create the staging and working tree entries
2. User clicks the Working Tree option
   1. GetOpenEligibleDocuments
   2. CreateDocumentSnapshotForWorkingTree - run for each open document 
   2. CreateDocumentSnapshotForCommit - run for each open document for the "index" option
   3. CreateDiff - run for each open document
   4. Display diffs in the tree view
3. User clicks the Staging option
   6. GetStagedFilePaths - checks both FCStd and snapshot files in the index
   7. CreateDocumentSnapshotForCommit - for each one get snapshot from index
   8. CreateDocumentSnapshotForCommit - for each one get snapshot from HEAD
   9. CreateDiff - for each one
   9. Display diffs in the tree view
4. User clicks a Commit
   5. GetCommittedFilePaths - checks both FCStd and snapshot files in the commit
   6. CreateDocumentSnapshotForCommit - for each one at commit
   7. CreateDocumentSnapshotForCommit - for each one at commit~1
   8. CreateDiff - for each one at commit
   9. Display diffs in the tree view

## Domain Entities

- To add:
    - GitRepository: with properties "name" and "absolute_path". "name" is the directory name of the git root
    - GitCommit: with properties "id" (the commit hash), "message", "author", and "timestamp"
- To modify:
    - DiffResult: should contain the Snapshots themselves

## Decisions

- When a commit is selected, for each FCStd file that has changed that does NOT have a corresponding YAML snapshot, it should add a bare document entry into the diff with text "no snapshot found"
    - Similarly, if the commit does contain a snapshot but the previous commit does not, display text "previous commit snapshot missing"
- Application state is stored in a simple in-memory object owned by the presentation layer. For MVP, this stores only the active `GitRepository` instance, which is created once at startup and reused across all git-related actions. Future enhancements may add observable properties using Qt signals.
  - Other UI state lives in the view layer: commit list and selected entry are stored in the sidebar QTreeWidget, and diff results are stored in the presenter (for property lookup callbacks).

## Out of Scope

- git branching (it always uses current branch)
- git merging
- git reset
- all other git commands

## Features to remove

- Ability to create custom in-memory snapshots and see them in the list

## Future

- Comparing two arbitrary commits (currently compares only to the previous commit)
- Resetting files from staging (must be done manually for now)
- Ability to create a repository in a given directory (must be done manually)
- Ability to switch git repositories which were detected from open documents
- File renamed detection and tracking
