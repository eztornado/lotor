/**
 * Punto de entrada de la API. Reexporta los clientes por juego para mantener
 * compatibilidad con los imports existentes.
 *
 * - El Gordo de la Primitiva -> `./gordo`
 * - Bonoloto -> `./bonoloto`
 * - Cliente HTTP base -> `./client`
 */
export { api, API_BASE_URL } from './client'
export * from './gordo'
export * from './bonoloto'
export { default } from './client'
