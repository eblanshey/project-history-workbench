# Git Repository Tests

Manual test cases for git repository detection and commit history features.

## Git Repository Detection

### Test Case 1: No Files Open

**Steps:**
1. Ensure no documents are open in FreeCAD
2. Switch to the Diff Workbench (View → Workbenches → Diff)

**Expected Result:**
- The repository info area displays: "No git repository detected"
- The text appears in gray, italic style
- A refresh button (circular arrow icon) appears to the right of the repository info
- No error messages or exceptions in the console

---

### Test Case 2: Files Open but No Active Git Repository

**Steps:**
1. Create a new document (File → New)
2. Save the document to a location outside any git repository (e.g., `/tmp/test.FCStd`)
3. Switch to the Diff Workbench (View → Workbenches → Diff)

**Expected Result:**
- The repository info area displays: "No git repository detected"
- The text appears in gray, italic style
- A refresh button (circular arrow icon) appears to the right of the repository info
- No error messages or exceptions in the console

---

### Test Case 3: Files Open with 1 Git Repository

**Steps:**
1. Open a document that is located within a git repository (e.g., `tests/freecad/BasicFile.FCStd` in this project)
2. Switch to the Diff Workbench (View → Workbenches → Diff)

**Expected Result:**
- The repository info appears ABOVE the "History" label
- The repository info area displays the repository name and path in format: `freecad_diff_workbench (/home/user/Repositories/freecad_diff_workbench)`
- The actual path will vary based on your installation location
- The text appears in bold style
- The repository name matches the directory name containing the `.git` folder
- A refresh button (circular arrow icon) appears to the right of the repository info
- No error messages or exceptions in the console

---

### Test Case 4: Files Open with Multiple Git Repositories

**Steps:**
1. Open a document from Git Repository A (e.g., `/home/user/project_a/file.FCStd`)
2. Open another document from Git Repository B (e.g., `/home/user/project_b/file.FCStd`)
3. Ensure one document is active (click on it in the document window)
4. Switch to the Diff Workbench (View → Workbenches → Diff)

**Expected Result:**
- The repository info appears ABOVE the "History" label
- The repository info area displays the git repository of the **active** document only
- Format: `project_name (/path/to/project)`
- The displayed repository corresponds to the document that currently has focus
- A refresh button (circular arrow icon) appears to the right of the repository info
- No error messages or exceptions in the console
- Note: Only ONE repository is shown at a time (the active document's repository)

---

### Additional Verification: Refresh Button Functionality

After switching workbenches in any test case above, you can optionally verify the refresh button functionality:

**Steps:**
1. After the initial detection completes, switch to a different workbench (e.g., Part Design)
2. Switch back to the Diff Workbench
3. Click the refresh button (circular arrow icon) next to the repository info

**Expected Result:**
- The git repository detection is re-triggered
- The same result is displayed as before (repository info remains consistent)
- If a valid git repository exists, it should be detected and displayed again
- If no git repository exists, "No git repository detected" should be displayed

---

## Git Commits (History Widget)

### Commit List Display and Interaction

**Steps:**
1. Open a document that is located within a git repository with existing commits
2. Switch to the Diff Workbench (View → Workbenches → Diff)
3. Observe the "History" label above the commit list
4. Verify each commit in the list displays:
   - 7-character commit hash
   - Author name
   - Timestamp
   - First line of commit message
5. Verify no commit is automatically selected (no highlight)
6. Hover the mouse cursor over a commit item to see the tooltip
7. Verify the tooltip displays the **full** commit message (including any body text after the first line)

**Expected Result:**
- "History" label appears above the list (replacing the old "Snapshots" label)
- Each commit displays: `a1b2c3d John Doe 2024-01-15 10:30` on line 1, followed by the first line of the message on line 2
- Commits are sorted with newest first
- No commit is highlighted/selected after loading
- Hovering shows a tooltip with the complete commit message (subject and body)

**Expected Result (continued):**
- If the repository has no commits, the list appears empty (no error)
- If git command fails, an empty list displays with no crash