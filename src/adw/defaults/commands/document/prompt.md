# Document Phase - PR Description Generation

Generate a structured Pull Request description for the implemented feature.

## Feature Description

{{feature_description}}

## Implementation Summary

{{implementation}}

## Git Changes

**Available Build Artifacts:**
{{artifacts.build.*}}

## Evidence

**Available Validate Artifacts:**
{{artifacts.validate.*}}

## Instructions

Generate a GitHub-flavored Markdown PR description with the following structure:

1. **Summary** (1-2 sentences): Concise description of what this PR accomplishes
2. **Changes**: Bullet list of key changes made (derived from the build artifacts above)
3. **Testing**: How the changes were verified (from validate artifacts/evidence)
4. **Evidence**: Links to relevant evidence items if available (screenshots, API responses, etc.)

Use the artifact information above to construct the PR description:
- If diff_stats is available, include file counts and line changes
- If evidence_manifest is available, reference evidence items and screenshots
- If no evidence is available, note "No visual evidence captured"

## Output Format

Your response MUST be a valid PR description in the following format:

```markdown
## Summary

[1-2 sentence summary of the PR]

## Changes

- [Change 1]
- [Change 2]
- [Change 3]

## Testing

[Description of testing performed]

## Evidence

[Links to evidence or "No visual evidence captured" if none]
```

## Constraints

- Maximum length: ~4000 characters (GitHub PR description limit)
- Use relative paths for any file references
- If evidence includes screenshots, include them as markdown image links
- Focus on the "why" and impact, not just the "what"
