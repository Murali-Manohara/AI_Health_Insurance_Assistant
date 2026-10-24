import React from 'react';

export function PlanSelector({ selectedCategory, onSelectCategory, disabled = false }) {
  return (
    <div className="form-group">
      <label htmlFor="category-select" className="form-label">
        Insurance Category
      </label>
      <select
        id="category-select"
        className="form-select"
        value={selectedCategory}
        onChange={(e) => onSelectCategory(e.target.value)}
        disabled={disabled}
      >
        <option value="customer">Customer Insurance</option>
        <option value="employee">Employee Insurance</option>
      </select>
    </div>
  );
}
