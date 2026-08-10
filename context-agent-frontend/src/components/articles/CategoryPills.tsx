import type { Category } from '../../api/types'

interface CategoryPillsProps {
  categories: Category[]
  selected: string | null
  onSelect: (name: string | null) => void
}

export function CategoryPills({ categories, selected, onSelect }: CategoryPillsProps) {
  return (
    <div className="category-pills">
      <button
        type="button"
        className={`pill${selected === null ? ' active' : ''}`}
        onClick={() => onSelect(null)}
      >
        All
      </button>
      {categories.map((category) => (
        <button
          key={category.id}
          type="button"
          className={`pill${selected === category.name ? ' active' : ''}`}
          onClick={() => onSelect(category.name)}
        >
          {category.name}
        </button>
      ))}
    </div>
  )
}
