enum ComplaintCustomerScope {
  own,
  assigned,
  all,
}

ComplaintCustomerScope complaintCustomerScopeForRole(String? role) {
  final normalized = (role ?? '').trim().toUpperCase();

  if (normalized == 'CUSTOMER') {
    return ComplaintCustomerScope.own;
  }

  if (normalized == 'ENGINEER') {
    return ComplaintCustomerScope.assigned;
  }

  // Office staff register complaints for the whole business, so they need
  // the complete customer directory just like Admin/Manager. Other staff
  // roles keep the historical all-customer behavior unless restricted by
  // the backend.
  return ComplaintCustomerScope.all;
}
