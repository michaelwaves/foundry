import { useMDXComponents as getThemeComponents } from 'nextra-theme-docs'


const themeComponents = getThemeConponents()
export function useMDXComponents(conponents) {
    return {
        ...themeComponents,
        ...components
    }
}