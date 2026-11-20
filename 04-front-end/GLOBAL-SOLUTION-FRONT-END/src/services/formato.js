const formatoData = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short' });
const formatoDataHora = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' });

export const formatarData = (iso) => formatoData.format(new Date(iso));
export const formatarDataHora = (iso) => formatoDataHora.format(new Date(iso));
