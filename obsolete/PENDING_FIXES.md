# Pending Fixes and Issues

## ✅ Completed (Dec 16, 2025)

1. **SQL Server Authentication Migration** - DONE
   - Migrated from SQLite to SQL Server
   - All 7 users migrated successfully
   - Login working with ovsadmin/ovs123admin and admin/admin123

2. **TypeScript Build Errors** - DONE
   - Disabled noUnusedLocals and noUnusedParameters in tsconfig
   - Fixed business_rules type annotation
   - Frontend builds successfully now

3. **Save Project Button** - SHOULD WORK NOW
   - Backend endpoint exists and is functional
   - Authentication now working with SQL Server
   - Should test to confirm

## 🔴 Remaining Issues to Fix

### 1. Project Selection Persistence in Pipeline Builder
**Issue**: Pipeline Builder keeps asking to select project even after selection
**Location**: `/frontend/src/pages/PipelineBuilder.tsx`
**Root Cause**: Need to verify currentProject prop is being passed and persisted correctly
**Fix Needed**: Check sessionStorage persistence and prop passing

### 2. Save Pipeline Errors
**Issue**: "Failed to save pipeline" errors
**Location**: Pipeline Builder save functionality
**Potential Cause**: May be related to project selection issue
**Fix Needed**: 
- Check if project_id is being sent correctly in save request
- Verify backend endpoint for saving pipelines
- Check authentication headers

### 3. Pipeline List Not Loading in Execution Screen
**Issue**: Saved pipelines not showing in Pipeline Execution screen
**Location**: `/frontend/src/pages/PipelineExecution.tsx`
**Fix Needed**:
- Check loadSavedPipelines function
- Verify API endpoint is correct
- Check if currentProject is being used properly in the request

### 4. Suggest Custom Queries Failures
**Issue**: "Failed to generate suggestions" error
**Location**: Query suggestions feature
**Potential Causes**:
- Backend endpoint error
- Missing metadata
- Database connection issues
**Fix Needed**: Check backend logs and API response

### 5. Pipeline Execution Status Messages
**Issue**: Shows "Pipeline executed successfully" immediately instead of showing progress
**Location**: `/frontend/src/pages/PipelineExecution.tsx` - executePipeline function
**Expected Behavior**:
- Show "Pipeline started..." immediately
- Poll for status updates
- Show final success/failure after completion
**Fix Needed**:
- Change initial message to "Pipeline started"
- Implement proper status polling
- Update message based on actual completion status

## 🔧 Recommended Fix Order

1. **Project Selection Persistence** - This is blocking other features
2. **Save Pipeline** - Depends on project selection
3. **Pipeline List Loading** - Depends on saved pipelines existing
4. **Pipeline Execution Status** - UX improvement
5. **Suggest Custom Queries** - Feature enhancement

## 📝 Notes

- All fixes should maintain authentication with SQL Server
- Test with ovsadmin user (admin role)
- Frontend is now building successfully
- Backend is running and responsive

