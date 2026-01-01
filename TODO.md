# TODO

## Fixed Issues
- [x] Fixed 404 error for reject application button by updating URL patterns
  - Changed main URL from 'jobs/' to 'job/' in KonnectAble/urls.py
  - Changed reject URL pattern from 'application/<int:application_id>/reject/' to 'reject/<int:application_id>/' in jobPanel/urls.py
  - Updated JavaScript in job_detail.html to use the new URL '/job/reject/${currentApplicationId}/'

## Pending Tasks
- [ ] Test the reject functionality to ensure it works correctly
- [ ] Check if other URLs need updating due to the change from 'jobs/' to 'job/'
