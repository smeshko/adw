# Report Issue Validation Checklist

## Required Fields

- [ ] Issue title provided and descriptive
- [ ] Severity selected (Critical/Major/Minor)
- [ ] Type selected (Bug/UX Issue/Regression)
- [ ] Component identified
- [ ] Description provided
- [ ] Reproduction steps documented
- [ ] Expected behavior described
- [ ] Actual behavior described
- [ ] Impact explained

## File Operations

- [ ] Issues directory exists or was created
- [ ] Assets directory exists or was created (if evidence provided)
- [ ] Issue file created with correct naming: `ISS-{number}-{slug}.md`
- [ ] All template placeholders replaced with actual values

## Evidence Handling

- [ ] Screenshot paths validated (if provided)
- [ ] Screenshots copied to assets folder with ISS prefix
- [ ] Markdown image references generated correctly
- [ ] Log file paths validated (if provided)
- [ ] Log files copied to assets folder with ISS prefix
- [ ] Markdown links generated correctly

## Sprint Status Updates

- [ ] sprint-status.yaml loaded successfully
- [ ] issue_counter incremented
- [ ] issues section exists or was created
- [ ] Issue entry added with status: reported
- [ ] For Critical: bugfix-ISS-{number} added to development_status
- [ ] For Major: ux-fix-ISS-{number} added to development_status
- [ ] sprint-status.yaml saved preserving comments and structure

## Severity Routing

### Critical Issues
- [ ] Bugfix story key generated
- [ ] Entry added to development_status with backlog status
- [ ] Issue file updated with fix story reference
- [ ] User prompted to create bugfix story

### Major Issues
- [ ] UX-fix story key generated
- [ ] Entry added to development_status with backlog status
- [ ] Issue file updated with fix story reference
- [ ] User prompted to create fix story

### Minor Issues
- [ ] No story entry created
- [ ] User informed issue added to backlog

## Final Verification

- [ ] Issue file contains all required sections
- [ ] All markdown formatting is correct
- [ ] Relative paths to assets are valid
- [ ] Sprint status YAML is valid syntax
- [ ] Summary output shown to user
- [ ] Next steps provided based on severity
