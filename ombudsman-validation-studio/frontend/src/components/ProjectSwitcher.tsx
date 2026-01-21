import { useState } from 'react';
import { Chip, Menu, MenuItem, ListItemIcon, ListItemText, Divider, Box } from '@mui/material';
import FolderOpenIcon from '@mui/icons-material/FolderOpen';
import CheckIcon from '@mui/icons-material/Check';
import AddIcon from '@mui/icons-material/Add';
import SettingsIcon from '@mui/icons-material/Settings';
import ArrowDropDownIcon from '@mui/icons-material/ArrowDropDown';

interface Project {
    project_id: string;
    name: string;
    description: string;
    created_at: string;
    updated_at: string;
    sql_database: string;
    sql_schemas: string[];
    snowflake_database: string;
    snowflake_schemas: string[];
    schema_mappings: { [key: string]: string };
}

interface ProjectSwitcherProps {
    currentProject: Project | null;
    allProjects: Project[];
    onProjectChange: (project: Project) => void;
    onCreateNew: () => void;
    onManageAll: () => void;
}

export default function ProjectSwitcher({
    currentProject,
    allProjects,
    onProjectChange,
    onCreateNew,
    onManageAll
}: ProjectSwitcherProps) {
    const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
    const open = Boolean(anchorEl);

    const handleClick = (event: React.MouseEvent<HTMLElement>) => {
        setAnchorEl(event.currentTarget);
    };

    const handleClose = () => {
        setAnchorEl(null);
    };

    const handleProjectSelect = (project: Project) => {
        onProjectChange(project);
        handleClose();
    };

    const handleCreateNew = () => {
        onCreateNew();
        handleClose();
    };

    const handleManageAll = () => {
        onManageAll();
        handleClose();
    };

    if (!currentProject) {
        return null;
    }

    return (
        <>
            <Chip
                label={`Project: ${currentProject.name}`}
                icon={<FolderOpenIcon sx={{ color: 'white !important' }} />}
                deleteIcon={<ArrowDropDownIcon sx={{ color: 'white !important' }} />}
                onDelete={handleClick}
                onClick={handleClick}
                sx={{
                    ml: 3,
                    bgcolor: 'rgba(255, 255, 255, 0.2)',
                    color: 'white',
                    fontWeight: 'bold',
                    border: '1px solid rgba(255, 255, 255, 0.3)',
                    cursor: 'pointer',
                    '&:hover': {
                        bgcolor: 'rgba(255, 255, 255, 0.3)'
                    },
                    '& .MuiChip-deleteIcon': {
                        color: 'white',
                        '&:hover': {
                            color: 'rgba(255, 255, 255, 0.8)'
                        }
                    }
                }}
            />
            <Menu
                anchorEl={anchorEl}
                open={open}
                onClose={handleClose}
                anchorOrigin={{
                    vertical: 'bottom',
                    horizontal: 'left',
                }}
                transformOrigin={{
                    vertical: 'top',
                    horizontal: 'left',
                }}
                PaperProps={{
                    sx: {
                        minWidth: 250,
                        mt: 1
                    }
                }}
            >
                {/* Project List */}
                {allProjects.map((project) => (
                    <MenuItem
                        key={project.project_id}
                        onClick={() => handleProjectSelect(project)}
                        selected={project.project_id === currentProject.project_id}
                    >
                        <ListItemIcon>
                            {project.project_id === currentProject.project_id ? (
                                <CheckIcon fontSize="small" color="primary" />
                            ) : (
                                <Box sx={{ width: 20 }} />
                            )}
                        </ListItemIcon>
                        <ListItemText
                            primary={project.name}
                            secondary={project.description?.substring(0, 40) || ''}
                        />
                    </MenuItem>
                ))}

                <Divider sx={{ my: 1 }} />

                {/* Actions */}
                <MenuItem onClick={handleCreateNew}>
                    <ListItemIcon>
                        <AddIcon fontSize="small" color="primary" />
                    </ListItemIcon>
                    <ListItemText primary="Create New Project" />
                </MenuItem>

                <MenuItem onClick={handleManageAll}>
                    <ListItemIcon>
                        <SettingsIcon fontSize="small" />
                    </ListItemIcon>
                    <ListItemText primary="Manage All Projects" />
                </MenuItem>
            </Menu>
        </>
    );
}
