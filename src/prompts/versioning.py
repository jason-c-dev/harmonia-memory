"""
Prompt versioning system for managing different versions of extraction prompts.
"""
import json
import hashlib
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict

from .template_engine import PromptTemplate
from .types import PromptVersion


@dataclass
class PromptVersionInfo:
    """Information about a prompt version."""
    version: str
    created_at: datetime
    description: str
    author: str
    template_hash: str
    performance_metrics: Dict[str, float] = None
    is_active: bool = True
    deprecated_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.performance_metrics is None:
            self.performance_metrics = {}


class PromptVersionManager:
    """Manages different versions of prompt templates."""
    
    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize prompt version manager.
        
        Args:
            storage_path: Path to store version metadata
        """
        self.storage_path = storage_path or Path("data/prompt_versions")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.versions: Dict[str, Dict[str, PromptVersionInfo]] = {}
        self.templates: Dict[str, Dict[str, PromptTemplate]] = {}
        self.active_versions: Dict[str, str] = {}
        
        self._load_versions()
    
    def _compute_template_hash(self, template: PromptTemplate) -> str:
        """Compute hash of template content for version tracking."""
        content = f"{template.template_text}{template.name}{template.version}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def register_template_version(self, template: PromptTemplate, 
                                description: str, author: str = "system") -> str:
        """
        Register a new version of a template.
        
        Args:
            template: PromptTemplate to register
            description: Description of this version
            author: Author of this version
            
        Returns:
            Version identifier
        """
        template_name = template.name
        version = template.version
        template_hash = self._compute_template_hash(template)
        
        # Initialize template versions if not exists
        if template_name not in self.versions:
            self.versions[template_name] = {}
            self.templates[template_name] = {}
        
        # Check if version already exists
        if version in self.versions[template_name]:
            existing_hash = self.versions[template_name][version].template_hash
            if existing_hash != template_hash:
                raise ValueError(f"Version {version} already exists with different content")
            return version
        
        # Create version info
        version_info = PromptVersionInfo(
            version=version,
            created_at=datetime.now(),
            description=description,
            author=author,
            template_hash=template_hash
        )
        
        # Store template and version info
        self.versions[template_name][version] = version_info
        self.templates[template_name][version] = template
        
        # Set as active if it's the first version or latest
        if not self.active_versions.get(template_name) or self._is_newer_version(version, self.active_versions.get(template_name, "0.0")):
            self.active_versions[template_name] = version
        
        self._save_versions()
        return version
    
    def get_template(self, template_name: str, version: str = None) -> Optional[PromptTemplate]:
        """
        Get a specific version of a template.
        
        Args:
            template_name: Name of the template
            version: Version to retrieve (uses active version if None)
            
        Returns:
            PromptTemplate or None if not found
        """
        if template_name not in self.templates:
            return None
        
        if version is None:
            version = self.active_versions.get(template_name)
            if not version:
                return None
        
        return self.templates[template_name].get(version)
    
    def get_active_template(self, template_name: str) -> Optional[PromptTemplate]:
        """Get the active version of a template."""
        return self.get_template(template_name)
    
    def set_active_version(self, template_name: str, version: str):
        """
        Set the active version for a template.
        
        Args:
            template_name: Name of the template
            version: Version to set as active
            
        Raises:
            ValueError: If template or version not found
        """
        if template_name not in self.versions:
            raise ValueError(f"Template '{template_name}' not found")
        
        if version not in self.versions[template_name]:
            raise ValueError(f"Version '{version}' not found for template '{template_name}'")
        
        self.active_versions[template_name] = version
        self._save_versions()
    
    def deprecate_version(self, template_name: str, version: str, reason: str = ""):
        """
        Deprecate a specific version.
        
        Args:
            template_name: Name of the template
            version: Version to deprecate
            reason: Reason for deprecation
        """
        if template_name not in self.versions or version not in self.versions[template_name]:
            raise ValueError(f"Template version '{template_name}:{version}' not found")
        
        version_info = self.versions[template_name][version]
        version_info.is_active = False
        version_info.deprecated_at = datetime.now()
        version_info.description += f" [DEPRECATED: {reason}]"
        
        # If this was the active version, find next best version
        if self.active_versions.get(template_name) == version:
            active_versions = [
                v for v, info in self.versions[template_name].items() 
                if info.is_active and v != version
            ]
            if active_versions:
                # Use the latest non-deprecated version
                latest = max(active_versions, key=lambda v: self.versions[template_name][v].created_at)
                self.active_versions[template_name] = latest
            else:
                del self.active_versions[template_name]
        
        self._save_versions()
    
    def update_performance_metrics(self, template_name: str, version: str, 
                                 metrics: Dict[str, float]):
        """
        Update performance metrics for a template version.
        
        Args:
            template_name: Name of the template
            version: Version to update
            metrics: Performance metrics dictionary
        """
        if template_name not in self.versions or version not in self.versions[template_name]:
            raise ValueError(f"Template version '{template_name}:{version}' not found")
        
        self.versions[template_name][version].performance_metrics.update(metrics)
        self._save_versions()
    
    def get_version_info(self, template_name: str, version: str = None) -> Optional[PromptVersionInfo]:
        """Get version information for a template."""
        if template_name not in self.versions:
            return None
        
        if version is None:
            version = self.active_versions.get(template_name)
            if not version:
                return None
        
        return self.versions[template_name].get(version)
    
    def list_template_versions(self, template_name: str) -> List[PromptVersionInfo]:
        """List all versions of a template."""
        if template_name not in self.versions:
            return []
        
        return list(self.versions[template_name].values())
    
    def list_templates(self) -> List[str]:
        """List all template names."""
        return list(self.versions.keys())
    
    def get_template_history(self, template_name: str) -> List[Dict[str, Any]]:
        """
        Get version history for a template.
        
        Args:
            template_name: Name of the template
            
        Returns:
            List of version history entries
        """
        if template_name not in self.versions:
            return []
        
        history = []
        for version, info in self.versions[template_name].items():
            entry = {
                'version': version,
                'created_at': info.created_at.isoformat(),
                'description': info.description,
                'author': info.author,
                'is_active': info.is_active,
                'performance_metrics': info.performance_metrics,
                'deprecated_at': info.deprecated_at.isoformat() if info.deprecated_at else None
            }
            history.append(entry)
        
        # Sort by creation date
        history.sort(key=lambda x: x['created_at'])
        return history
    
    def compare_versions(self, template_name: str, version1: str, version2: str) -> Dict[str, Any]:
        """
        Compare two versions of a template.
        
        Args:
            template_name: Name of the template
            version1: First version to compare
            version2: Second version to compare
            
        Returns:
            Comparison results
        """
        if template_name not in self.versions:
            raise ValueError(f"Template '{template_name}' not found")
        
        info1 = self.versions[template_name].get(version1)
        info2 = self.versions[template_name].get(version2)
        
        if not info1 or not info2:
            raise ValueError("One or both versions not found")
        
        template1 = self.templates[template_name][version1]
        template2 = self.templates[template_name][version2]
        
        return {
            'template_name': template_name,
            'version1': {
                'version': version1,
                'created_at': info1.created_at.isoformat(),
                'description': info1.description,
                'author': info1.author,
                'template_length': len(template1.template_text),
                'variables': template1.variables,
                'performance_metrics': info1.performance_metrics
            },
            'version2': {
                'version': version2,
                'created_at': info2.created_at.isoformat(),
                'description': info2.description,
                'author': info2.author,
                'template_length': len(template2.template_text),
                'variables': template2.variables,
                'performance_metrics': info2.performance_metrics
            },
            'differences': {
                'template_changed': info1.template_hash != info2.template_hash,
                'variables_changed': template1.variables != template2.variables,
                'newer_version': version2 if self._is_newer_version(version2, version1) else version1
            }
        }
    
    def _is_newer_version(self, version1: str, version2: str) -> bool:
        """Check if version1 is newer than version2."""
        try:
            # Simple semantic version comparison
            v1_parts = [int(x) for x in version1.split('.')]
            v2_parts = [int(x) for x in version2.split('.')]
            
            # Pad with zeros to same length
            max_len = max(len(v1_parts), len(v2_parts))
            v1_parts.extend([0] * (max_len - len(v1_parts)))
            v2_parts.extend([0] * (max_len - len(v2_parts)))
            
            return v1_parts > v2_parts
        except ValueError:
            # Fallback to string comparison
            return version1 > version2
    
    def _save_versions(self):
        """Save version metadata to storage."""
        metadata = {
            'versions': {},
            'active_versions': self.active_versions
        }
        
        # Convert version info to serializable format
        for template_name, versions in self.versions.items():
            metadata['versions'][template_name] = {}
            for version, info in versions.items():
                metadata['versions'][template_name][version] = {
                    'version': info.version,
                    'created_at': info.created_at.isoformat(),
                    'description': info.description,
                    'author': info.author,
                    'template_hash': info.template_hash,
                    'performance_metrics': info.performance_metrics,
                    'is_active': info.is_active,
                    'deprecated_at': info.deprecated_at.isoformat() if info.deprecated_at else None
                }
        
        # Save metadata
        metadata_file = self.storage_path / "versions.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Save templates separately
        for template_name, versions in self.templates.items():
            template_dir = self.storage_path / template_name
            template_dir.mkdir(exist_ok=True)
            
            for version, template in versions.items():
                template_file = template_dir / f"{version}.txt"
                with open(template_file, 'w') as f:
                    f.write(template.template_text)
    
    def _load_versions(self):
        """Load version metadata from storage."""
        metadata_file = self.storage_path / "versions.json"
        if not metadata_file.exists():
            return
        
        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            self.active_versions = metadata.get('active_versions', {})
            
            # Load version info
            for template_name, versions in metadata.get('versions', {}).items():
                self.versions[template_name] = {}
                self.templates[template_name] = {}
                
                for version, info_dict in versions.items():
                    # Reconstruct version info
                    version_info = PromptVersionInfo(
                        version=info_dict['version'],
                        created_at=datetime.fromisoformat(info_dict['created_at']),
                        description=info_dict['description'],
                        author=info_dict['author'],
                        template_hash=info_dict['template_hash'],
                        performance_metrics=info_dict.get('performance_metrics', {}),
                        is_active=info_dict.get('is_active', True),
                        deprecated_at=datetime.fromisoformat(info_dict['deprecated_at']) if info_dict.get('deprecated_at') else None
                    )
                    self.versions[template_name][version] = version_info
                    
                    # Load template content
                    template_file = self.storage_path / template_name / f"{version}.txt"
                    if template_file.exists():
                        with open(template_file, 'r') as f:
                            template_text = f.read()
                        
                        template = PromptTemplate(template_text, template_name, version)
                        self.templates[template_name][version] = template
                        
        except Exception as e:
            print(f"Warning: Failed to load prompt versions: {e}")
    
    def export_version(self, template_name: str, version: str, 
                      export_path: Path) -> Path:
        """
        Export a template version to a file.
        
        Args:
            template_name: Name of the template
            version: Version to export
            export_path: Path to export to
            
        Returns:
            Path to exported file
        """
        template = self.get_template(template_name, version)
        version_info = self.get_version_info(template_name, version)
        
        if not template or not version_info:
            raise ValueError(f"Template version '{template_name}:{version}' not found")
        
        export_data = {
            'metadata': asdict(version_info),
            'template': {
                'name': template.name,
                'version': template.version,
                'template_text': template.template_text,
                'variables': template.variables
            }
        }
        
        # Convert datetime objects to strings
        export_data['metadata']['created_at'] = version_info.created_at.isoformat()
        if version_info.deprecated_at:
            export_data['metadata']['deprecated_at'] = version_info.deprecated_at.isoformat()
        
        export_file = export_path / f"{template_name}_{version}.json"
        with open(export_file, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        return export_file