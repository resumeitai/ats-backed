"""
Resume version comparison service.
Provides deep diff between two resume content JSON objects.
"""
import difflib
from typing import Any, Dict, List


class ResumeComparator:
    """Compare two resume content dicts and produce a detailed diff report."""

    def __init__(self, content_a: dict, content_b: dict, label_a: str = 'Version A', label_b: str = 'Version B'):
        self.content_a = content_a or {}
        self.content_b = content_b or {}
        self.label_a = label_a
        self.label_b = label_b

    def compare(self) -> dict:
        """
        Run full comparison. Returns:
        {
            "summary": {"added_sections": [...], "removed_sections": [...], "modified_sections": [...], "unchanged_sections": [...]},
            "details": {<section_name>: <section_diff>, ...},
            "text_diff": "unified diff string",
            "change_count": int,
        }
        """
        keys_a = set(self.content_a.keys())
        keys_b = set(self.content_b.keys())

        added = sorted(keys_b - keys_a)
        removed = sorted(keys_a - keys_b)
        common = sorted(keys_a & keys_b)

        modified = []
        unchanged = []
        details = {}

        # Diff each common section
        for key in common:
            section_diff = self._diff_section(key, self.content_a[key], self.content_b[key])
            if section_diff['has_changes']:
                modified.append(key)
            else:
                unchanged.append(key)
            details[key] = section_diff

        # Added sections
        for key in added:
            details[key] = {
                'status': 'added',
                'has_changes': True,
                'new_value': self.content_b[key],
                'changes': [{'type': 'section_added', 'section': key}],
            }

        # Removed sections
        for key in removed:
            details[key] = {
                'status': 'removed',
                'has_changes': True,
                'old_value': self.content_a[key],
                'changes': [{'type': 'section_removed', 'section': key}],
            }

        # Generate unified text diff
        text_a = self._content_to_text(self.content_a)
        text_b = self._content_to_text(self.content_b)
        unified_diff = '\n'.join(difflib.unified_diff(
            text_a.splitlines(),
            text_b.splitlines(),
            fromfile=self.label_a,
            tofile=self.label_b,
            lineterm='',
        ))

        total_changes = sum(
            len(d.get('changes', []))
            for d in details.values()
        )

        return {
            'summary': {
                'added_sections': added,
                'removed_sections': removed,
                'modified_sections': modified,
                'unchanged_sections': unchanged,
            },
            'details': details,
            'text_diff': unified_diff,
            'change_count': total_changes,
        }

    def _diff_section(self, key: str, val_a: Any, val_b: Any) -> dict:
        """Diff a single section by type."""
        if val_a == val_b:
            return {'status': 'unchanged', 'has_changes': False, 'changes': []}

        changes = []

        if isinstance(val_a, dict) and isinstance(val_b, dict):
            changes = self._diff_dicts(key, val_a, val_b)
        elif isinstance(val_a, list) and isinstance(val_b, list):
            changes = self._diff_lists(key, val_a, val_b)
        elif isinstance(val_a, str) and isinstance(val_b, str):
            changes = self._diff_strings(key, val_a, val_b)
        else:
            changes = [{
                'type': 'value_changed',
                'section': key,
                'old': val_a,
                'new': val_b,
            }]

        return {
            'status': 'modified',
            'has_changes': len(changes) > 0,
            'changes': changes,
        }

    def _diff_dicts(self, section: str, dict_a: dict, dict_b: dict) -> List[dict]:
        """Diff two dicts field by field."""
        changes = []
        all_keys = sorted(set(list(dict_a.keys()) + list(dict_b.keys())))

        for k in all_keys:
            old_val = dict_a.get(k)
            new_val = dict_b.get(k)

            if old_val == new_val:
                continue
            elif old_val is None:
                changes.append({
                    'type': 'field_added',
                    'section': section,
                    'field': k,
                    'new': new_val,
                })
            elif new_val is None:
                changes.append({
                    'type': 'field_removed',
                    'section': section,
                    'field': k,
                    'old': old_val,
                })
            else:
                changes.append({
                    'type': 'field_changed',
                    'section': section,
                    'field': k,
                    'old': old_val,
                    'new': new_val,
                })

        return changes

    def _diff_lists(self, section: str, list_a: list, list_b: list) -> List[dict]:
        """Diff two lists, detecting added/removed/modified items."""
        changes = []
        max_len = max(len(list_a), len(list_b))

        for i in range(max_len):
            if i >= len(list_a):
                changes.append({
                    'type': 'item_added',
                    'section': section,
                    'index': i,
                    'new': list_b[i],
                })
            elif i >= len(list_b):
                changes.append({
                    'type': 'item_removed',
                    'section': section,
                    'index': i,
                    'old': list_a[i],
                })
            elif list_a[i] != list_b[i]:
                if isinstance(list_a[i], dict) and isinstance(list_b[i], dict):
                    field_changes = self._diff_dicts(f"{section}[{i}]", list_a[i], list_b[i])
                    changes.extend(field_changes)
                else:
                    changes.append({
                        'type': 'item_changed',
                        'section': section,
                        'index': i,
                        'old': list_a[i],
                        'new': list_b[i],
                    })

        return changes

    def _diff_strings(self, section: str, str_a: str, str_b: str) -> List[dict]:
        """Diff two strings using SequenceMatcher for highlighted changes."""
        if str_a == str_b:
            return []

        matcher = difflib.SequenceMatcher(None, str_a.split(), str_b.split())
        ratio = matcher.ratio()

        return [{
            'type': 'text_changed',
            'section': section,
            'old': str_a,
            'new': str_b,
            'similarity': round(ratio * 100, 1),
        }]

    @staticmethod
    def _content_to_text(content: dict) -> str:
        """Flatten resume content dict to text for unified diff."""
        lines = []
        for section, data in sorted(content.items()):
            lines.append(f"=== {section.upper()} ===")
            if isinstance(data, str):
                lines.append(data)
            elif isinstance(data, dict):
                for k, v in data.items():
                    lines.append(f"  {k}: {v}")
            elif isinstance(data, list):
                for i, item in enumerate(data):
                    if isinstance(item, dict):
                        lines.append(f"  [{i + 1}]")
                        for k, v in item.items():
                            lines.append(f"    {k}: {v}")
                    else:
                        lines.append(f"  - {item}")
            lines.append("")
        return '\n'.join(lines)
