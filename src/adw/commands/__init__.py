"""ADW commands module - command resolution and templates.

``resolver.CommandResolver`` resolves commands through a three-tier hierarchy:
1. Project level: .adw/commands/{name}/
2. User level: ~/.adw/commands/{name}/
3. Bundled level: Package defaults

``template.TemplateEngine`` renders their prompt templates.
"""
