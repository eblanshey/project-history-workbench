# Translations

This directory contains translation files for the Diff Workbench.

## Adding Translations

1. Add new language files as `<workbench_name>_<locale>.ts` (e.g., `diff_wb_es-ES.ts`)
2. Use FreeCAD's translation tools to extract translatable strings
3. Compile `.ts` files to `.qm` using `lrelease`

## File Naming Convention

- Format: `diff_wb_<language>-<country>.ts`
- Example: `diff_wb_en-US.ts`, `diff_wb_de-DE.ts`
